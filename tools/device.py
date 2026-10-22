#!/usr/bin/env python3
"""ADB preflight and recorded launcher recovery. Python standard library, no debloat.

Inspired by CleanYourTV's record-before-change workflow. Implemented for this
launcher's permissions and services; it does not replay their package lists.
"""
import argparse
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import struct
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET

PKG = "app.orchard.tv"
HOME = PKG + "/.MainActivity"
GUARD = PKG + "/" + PKG + ".guard.HomeGuardService"
LISTENER = PKG + "/" + PKG + ".guard.RevivalListener"
PERMISSION = "android.permission.WRITE_SECURE_SETTINGS"
OPS = ("SYSTEM_ALERT_WINDOW", "WRITE_SETTINGS", "APP_AUTO_START", "APP_ASSOC_START")
COMPONENT = re.compile(r"[A-Za-z_][\w.]*/[A-Za-z_.$][\w.$]*", re.ASCII)
MODES = {"allow", "ignore", "deny", "default", "foreground"}


def manifest_package(data):
    """Read manifest.package from plain XML or Android's binary XML, without an SDK dependency."""
    try:
        if data.lstrip().startswith(b"<"):
            root = ET.fromstring(data)
            return root.get("package") if root.tag == "manifest" else None
        if len(data) < 8 or struct.unpack_from("<H", data)[0] != 3:
            return None
        strings = []
        pos = struct.unpack_from("<H", data, 2)[0]
        while pos + 8 <= len(data):
            kind, header, size = struct.unpack_from("<HHI", data, pos)
            if header < 8 or size < header or pos + size > len(data):
                return None
            if kind == 1:
                count, _, flags, start = struct.unpack_from("<IIII", data, pos + 8)
                if count > size // 4 or header + count * 4 > size:
                    return None
                for i in range(count):
                    at = pos + start + struct.unpack_from("<I", data, pos + header + i * 4)[0]
                    if flags & 0x100:
                        def length8(at):
                            first = data[at]
                            return (((first & 0x7f) << 8) | data[at + 1], at + 2) if first & 0x80 else (first, at + 1)
                        _, at = length8(at)
                        length, at = length8(at)
                        strings.append(data[at:at + length].decode("utf-8"))
                    else:
                        length = struct.unpack_from("<H", data, at)[0]
                        at += 2
                        if length & 0x8000:
                            length = ((length & 0x7fff) << 16) | struct.unpack_from("<H", data, at)[0]
                            at += 2
                        strings.append(data[at:at + length * 2].decode("utf-16-le"))
            elif kind == 0x102:
                base = pos + header
                name = struct.unpack_from("<I", data, base + 4)[0]
                if strings[name] == "manifest":
                    start, stride, count = struct.unpack_from("<HHH", data, base + 8)
                    if stride < 20 or base + start + count * stride > pos + size:
                        return None
                    for i in range(count):
                        at = base + start + i * stride
                        namespace, key, raw = struct.unpack_from("<III", data, at)
                        if namespace == 0xffffffff and strings[key] == "package":
                            value = raw if raw != 0xffffffff else struct.unpack_from("<I", data, at + 16)[0]
                            return strings[value] if raw != 0xffffffff or data[at + 15] == 3 else None
            pos += size
    except (IndexError, struct.error, UnicodeError, ET.ParseError):
        return None
    return None


def expanded(component):
    if not COMPONENT.fullmatch(component):
        raise ValueError("Invalid activity/service component: " + component)
    package, name = component.split("/", 1)
    return package + "/" + (package + name if name.startswith(".") else name)


def members(raw):
    return [value for value in raw.split(":") if value and value != "null"]


def contains(raw, component):
    return any(expanded(value) == expanded(component) for value in members(raw))


def without(raw, component):
    return [value for value in members(raw) if expanded(value) != expanded(component)]


class Adb:
    def __init__(self, host):
        if not re.fullmatch(r"[A-Za-z0-9._-]+(?::[0-9]{1,5})?", host) or host.startswith("-"):
            raise ValueError("TV must be a hostname or IPv4 address, optionally followed by :port")
        if not shutil.which("adb"):
            raise ValueError("adb not found. Install Android platform-tools and add it to PATH.")
        self.serial = host if ":" in host else host + ":5555"
        self.call("connect", self.serial)
        if self.call("-s", self.serial, "get-state").strip() != "device":
            raise ValueError("TV is not authorized. Accept the debugging prompt on the TV.")

    def call(self, *args, timeout=45):
        result = subprocess.run(["adb", *args], capture_output=True, text=True, timeout=timeout)
        output = (result.stdout + result.stderr).strip()
        if result.returncode or re.search(r"(^|\n)(?:Error:|Failure|Failed|Exception|(?:java\.lang\.)?(?:SecurityException|IllegalArgumentException)|Unknown command|Unknown operation|Permission denial)", output):
            raise RuntimeError("adb " + shlex.join(args) + ": " + output)
        return output

    def shell(self, *args):
        # adb joins remote arguments before passing them to the TV's shell.
        return self.call("-s", self.serial, "shell", shlex.join(args))

    def optional(self, *args):
        try:
            return self.shell(*args)
        except RuntimeError:
            return None

    def home(self):
        answer = self.optional("cmd", "package", "resolve-activity", "--brief", "--user", "0",
                               "-a", "android.intent.action.MAIN", "-c", "android.intent.category.HOME")
        candidate = (answer or "").splitlines()[-1:] or [""]
        return candidate[0] if COMPONENT.fullmatch(candidate[0]) else None

    def identity(self):
        user = self.shell("am", "get-current-user")
        if user != "0":
            raise ValueError("This installer supports the primary TV user (0) only; current user: " + user)
        serial = self.shell("getprop", "ro.serialno")
        if serial.lower() in ("", "unknown", "null"):
            serial = self.shell("settings", "get", "secure", "android_id")
        if serial.lower() in ("", "unknown", "null"):
            raise ValueError("No stable device ID; refusing to associate recovery with an IP address alone.")
        return {"id": serial, "model": self.shell("getprop", "ro.product.model"),
                "brand": self.shell("getprop", "ro.product.manufacturer"),
                "android": self.shell("getprop", "ro.build.version.release"),
                "sdk": self.shell("getprop", "ro.build.version.sdk")}


def timestamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def record_path(directory, identity):
    key = hashlib.sha256((identity["id"] + "\0" + identity["model"]).encode()).hexdigest()[:24]
    return directory / (key + ".json")


def atomic_write(path, record):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, name = tempfile.mkstemp(prefix=".recovery-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(record, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def load_record(path, identity):
    record = json.loads(path.read_text())
    if record.get("version") != 1 or record.get("package") != PKG:
        raise ValueError("Unsupported recovery record; leave it intact: " + str(path))
    for key in ("id", "model"):
        if record.get("device", {}).get(key) != identity[key]:
            raise ValueError("Recovery record belongs to a different TV")
    home = record.get("home")
    if home is not None:
        expanded(home)
    if not isinstance(record.get("ops"), dict) or set(record["ops"]) != set(OPS) or any(not (value is None or isinstance(value, str) and value in MODES) for value in record["ops"].values()):
        raise ValueError("Invalid app-op recovery state")
    for key in ("installed", "write_secure", "guard", "listener"):
        if not isinstance(record.get(key), bool):
            raise ValueError("Invalid recovery flag: " + key)
    if record.get("accessibility_enabled") not in ("null", "0", "1") or not isinstance(record.get("accessibility_services"), str):
        raise ValueError("Invalid accessibility recovery state")
    for value in members(record["accessibility_services"]):
        expanded(value)
    if record.get("status") not in ("active", "restored"):
        raise ValueError("Invalid recovery status")
    if not isinstance(record.get("created"), str):
        raise ValueError("Invalid recovery timestamp")
    if record["home"] is None or record["home"].split("/")[0] in (PKG, "android"):
        raise ValueError("Recovery record has no original launcher")
    return record


def snapshot(adb, identity, original_home=None):
    home = original_home or adb.home()
    if not home or expanded(home).split("/")[0] in (PKG, "android"):
        raise ValueError("Choose the original launcher first, or supply --original-home PACKAGE/ACTIVITY. No TV settings were changed.")
    # Verify an explicitly supplied original launcher exists before saving a usable-looking record.
    if original_home and not adb.shell("pm", "path", home.split("/")[0]).startswith("package:"):
        raise ValueError("The original launcher package is not installed")
    installed = (adb.optional("pm", "path", PKG) or "").startswith("package:")
    dump = adb.shell("dumpsys", "package", PKG) if installed else ""
    ops = {}
    for op in OPS:
        raw = adb.optional("cmd", "appops", "get", "--user", "0", PKG, op) if installed else None
        if installed and raw is None and op in OPS[:2]:
            raise ValueError("Cannot record the original app-op: " + op)
        match = re.search(r"\b" + op + r":\s*(allow|ignore|deny|default|foreground)\b", raw or "")
        ops[op] = match.group(1) if match else ("default" if raw is not None or op in OPS[:2] else None)
    accessibility = adb.shell("settings", "get", "secure", "enabled_accessibility_services")
    accessibility_enabled = adb.shell("settings", "get", "secure", "accessibility_enabled")
    if accessibility_enabled not in ("null", "0", "1"):
        raise ValueError("Cannot read the original accessibility switch")
    return {"version": 1, "package": PKG, "created": timestamp(), "status": "active", "device": identity,
            "home": home, "installed": installed, "ops": ops,
            "write_secure": bool(re.search(re.escape(PERMISSION) + r":\s*granted=true", dump)),
            "accessibility_services": accessibility, "accessibility_enabled": accessibility_enabled,
            "guard": contains(accessibility, GUARD),
            "listener": contains(adb.shell("settings", "get", "secure", "enabled_notification_listeners"), LISTENER)}


def prepare_record(adb, identity, path, original_home=None):
    if path.exists():
        record = load_record(path, identity)
        if record["status"] == "active":
            print("Keeping the recovery record from " + record["created"])
            return record
        # Retain the completed cycle for inspection before recording a new baseline.
        archive = path.with_name(path.stem + "-" + hashlib.sha256(path.read_bytes()).hexdigest()[:12] + ".restored.json")
        if not archive.exists():
            shutil.copy2(path, archive)
    record = snapshot(adb, identity, original_home)
    atomic_write(path, record)
    print("Original launcher and permissions saved: " + str(path))
    return record


def set_membership(adb, setting, component, enabled):
    current = adb.shell("settings", "get", "secure", setting)
    updated = without(current, component)
    if enabled:
        updated.append(component)
    if updated:
        adb.shell("settings", "put", "secure", setting, ":".join(updated))
    else:
        adb.shell("settings", "delete", "secure", setting)
    if contains(adb.shell("settings", "get", "secure", setting), component) != enabled:
        raise RuntimeError("Service membership did not change: " + setting)


def install(adb, args, identity, path):
    apk = Path(args.apk).expanduser().resolve()
    if not apk.is_file() or not zipfile.is_zipfile(apk):
        raise ValueError("Not an APK file: " + str(apk))
    with zipfile.ZipFile(apk) as package:
        if "AndroidManifest.xml" not in package.namelist():
            raise ValueError("APK has no AndroidManifest.xml")
        if package.getinfo("AndroidManifest.xml").file_size > 2 * 1024 * 1024:
            raise ValueError("APK manifest is too large")
        if manifest_package(package.read("AndroidManifest.xml")) != PKG:
            raise ValueError("APK is not the expected launcher package (" + PKG + ")")
    print(json.dumps({"device": identity, "home": adb.home(), "apk": str(apk),
                      "flavor": args.flavor, "launcher_only": args.launcher_only, "force_guard": args.force_guard,
                      "recovery": str(path)}, ensure_ascii=False, indent=2))
    if args.preview:
        print("Preview only: no APK installed and no TV settings changed.")
        return
    if not args.launcher_only:
        prepare_record(adb, identity, path, args.original_home)
    # adb refuses different signing keys. Never auto-uninstall and never bypass the firmware verifier.
    print(adb.call("-s", adb.serial, "install", "-r", str(apk), timeout=180))
    if not adb.shell("pm", "path", PKG).startswith("package:"):
        raise ValueError("Expected launcher package was not found after installation")
    if args.launcher_only:
        print("APK installed. Open it from the TV's apps list to test; no takeover permissions were granted.")
        return
    if args.flavor == "standard":
        adb.optional("cmd", "package", "set-home-activity", "--user", "0", HOME)
        current = adb.home()
        if current is None or expanded(current) != expanded(HOME):
            adb.optional("cmd", "role", "add-role-holder", "--user", "0", "android.app.role.HOME", PKG)
    resolved = adb.home()
    if args.force_guard or args.flavor == "guard" or not resolved or expanded(resolved) != expanded(HOME):
        print("Default HOME unavailable; enabling the recorded Home Guard takeover.")
        adb.shell("pm", "grant", PKG, PERMISSION)
        adb.shell("cmd", "appops", "set", "--user", "0", PKG, "SYSTEM_ALERT_WINDOW", "allow")
        adb.shell("cmd", "notification", "allow_listener", LISTENER, "0")
        set_membership(adb, "enabled_accessibility_services", GUARD, True)
        adb.shell("settings", "put", "secure", "accessibility_enabled", "1")
    adb.shell("am", "start", "-W", "-n", HOME)
    print("Installation commands completed. Verify Home, reboot and standby on the TV. Restore with TV=... bash tools/restore.sh")


def restore(adb, args, identity, path):
    if not path.exists():
        raise ValueError("No recovery record for this TV. No settings were changed; select the original launcher manually.")
    record = load_record(path, identity)
    if args.uninstall and record["installed"]:
        raise ValueError("The app existed before installation; refusing to uninstall its existing data. Restore without --uninstall.")
    if record["status"] == "restored":
        print("This recovery cycle is already restored; no TV settings were changed.")
        return
    if args.preview:
        print(json.dumps(record, ensure_ascii=False, indent=2))
        print("Preview only: no TV settings changed.")
        return
    failures = []
    package_present = (adb.optional("pm", "path", PKG) or "").startswith("package:")
    if record["installed"] and not package_present:
        raise ValueError("The previously installed app has been removed; this record cannot recover its APK or data.")

    def attempt(label, action):
        try:
            action()
        except (RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
            failures.append(label + ": " + str(error))

    # Stop self-revival before changing service bindings. Keep unrelated services added since install.
    if package_present:
        attempt("stop launcher", lambda: adb.shell("am", "force-stop", PKG))
        attempt("notification listener", lambda: adb.shell("cmd", "notification", "allow_listener" if record["listener"] else "disallow_listener", LISTENER, "0"))
    attempt("accessibility", lambda: set_membership(adb, "enabled_accessibility_services", GUARD, record["guard"]))
    remaining = adb.shell("settings", "get", "secure", "enabled_accessibility_services")
    # Restore the global switch only if doing so cannot switch off a newly enabled service.
    if set(without(remaining, GUARD)) == set(without(record["accessibility_services"], GUARD)):
        old = record["accessibility_enabled"]
        attempt("accessibility switch", lambda: adb.shell("settings", "delete", "secure", "accessibility_enabled")
                if old == "null" else adb.shell("settings", "put", "secure", "accessibility_enabled", old))
    for op, mode in record["ops"].items():
        if mode is not None and package_present:
            attempt(op, lambda op=op, mode=mode: adb.shell("cmd", "appops", "set", "--user", "0", PKG, op, mode))
    if package_present:
        attempt("secure-settings permission", lambda: adb.shell("pm", "grant" if record["write_secure"] else "revoke", PKG, PERMISSION))
    current_listeners = adb.shell("settings", "get", "secure", "enabled_notification_listeners")
    if contains(current_listeners, LISTENER) != record["listener"]:
        failures.append("Notification listener state did not match the original record.")
    # Explicit component also reverses the set-home-activity fallback, rather than only removing a role.
    adb.optional("cmd", "role", "remove-role-holder", "--user", "0", "android.app.role.HOME", PKG)
    attempt("original HOME", lambda: adb.shell("cmd", "package", "set-home-activity", "--user", "0", record["home"]))
    resolved = adb.home()
    if not resolved or expanded(resolved) != expanded(record["home"]):
        failures.append("HOME did not resolve to the recorded original launcher; select it in TV settings.")
    if failures:
        raise RuntimeError("Recovery incomplete; record retained for retry:\n" + "\n".join(failures))
    if args.uninstall:
        adb.call("-s", adb.serial, "uninstall", PKG)
    adb.shell("input", "keyevent", "KEYCODE_HOME")
    record["status"] = "restored"
    record["restored"] = timestamp()
    atomic_write(path, record)
    print("Restored original HOME: " + resolved + ". Recovery record retained: " + str(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("check", "install", "restore"))
    parser.add_argument("--apk", default=os.environ.get("APK_FILE"))
    parser.add_argument("--flavor", choices=("standard", "guard"), default="standard")
    parser.add_argument("--launcher-only", action="store_true")
    parser.add_argument("--force-guard", action="store_true", help="use Home Guard even when Android reports this app as default HOME")
    parser.add_argument("--preview", action="store_true")
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--original-home")
    parser.add_argument("--state-dir", type=Path, default=Path(__file__).resolve().parent.parent / "local" / "recovery")
    args = parser.parse_args()
    if not os.environ.get("TV"):
        parser.error("set TV to your TV's IP address")
    if args.action == "install" and not args.apk:
        parser.error("set APK_FILE or pass --apk")
    adb = Adb(os.environ["TV"])
    identity = adb.identity()
    path = record_path(args.state_dir, identity)
    if args.action == "check":
        print(json.dumps({"device": identity, "home": adb.home(), "recovery": str(path), "record_exists": path.exists()}, ensure_ascii=False, indent=2))
        return
    if args.preview:
        (install if args.action == "install" else restore)(adb, args, identity, path)
        return
    args.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (args.state_dir / ".lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        (install if args.action == "install" else restore)(adb, args, identity, path)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, ValueError, OSError, zipfile.BadZipFile, subprocess.TimeoutExpired) as exc:
        sys.exit(str(exc))

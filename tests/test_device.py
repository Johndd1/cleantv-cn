"""Exercise install -> retry -> recovery against a stateful TV double. No real TV is touched."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
import io
from contextlib import redirect_stdout

SPEC = importlib.util.spec_from_file_location("device", Path(__file__).resolve().parents[1] / "tools/device.py")
d = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(d)


class TV:
    serial = "tv.test:5555"

    def __init__(self):
        self.home_component = "com.vendor.home/.Main"
        self.installed = False
        self.write_secure = False
        self.settings = {"enabled_accessibility_services": "com.reader.service/.Reader",
                         "accessibility_enabled": "1", "enabled_notification_listeners": "com.other.app/.Listener"}
        self.ops = dict.fromkeys(d.OPS, "default")
        self.mutations = []
        self.fail_home = False
        self.refuse_takeover = False
        self.fail_install = False

    def home(self):
        return self.home_component

    def optional(self, *args):
        try:
            return self.shell(*args)
        except RuntimeError:
            return None

    def call(self, *args, **kwargs):
        if "install" in args:
            if self.fail_install:
                raise RuntimeError("INSTALL_FAILED_UPDATE_INCOMPATIBLE")
            self.installed = True
            self.mutations.append(("install",))
        if "uninstall" in args:
            self.installed = False
            self.mutations.append(("uninstall",))
        return "Success"

    def shell(self, *args):
        if args[:2] == ("pm", "path"):
            return "package:/data/app/base.apk" if args[2] != d.PKG or self.installed else ""
        if args[:2] == ("dumpsys", "package"):
            return d.PERMISSION + ": granted=" + str(self.write_secure).lower()
        if args[:2] == ("settings", "get"):
            return self.settings.get(args[3], "null")
        if args[:3] == ("cmd", "appops", "get"):
            return args[-1] + ": " + self.ops[args[-1]]
        self.mutations.append(args)
        if args[:2] == ("settings", "put"):
            self.settings[args[3]] = args[4]
        elif args[:2] == ("settings", "delete"):
            self.settings.pop(args[3], None)
        elif args[:3] == ("cmd", "appops", "set"):
            self.ops[args[-2]] = args[-1]
        elif args[:2] in (("pm", "grant"), ("pm", "revoke")):
            self.write_secure = args[1] == "grant"
        elif args[:2] == ("cmd", "notification"):
            listeners = d.without(self.settings["enabled_notification_listeners"], args[3])
            if args[2] == "allow_listener":
                listeners.append(args[3])
            self.settings["enabled_notification_listeners"] = ":".join(listeners)
        elif args[:3] == ("cmd", "package", "set-home-activity"):
            if self.fail_home or (args[-1] == d.HOME and self.refuse_takeover):
                raise RuntimeError("firmware refused HOME")
            self.home_component = args[-1]
        return ""


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        capture = redirect_stdout(io.StringIO())
        capture.__enter__()
        self.addCleanup(capture.__exit__, None, None, None)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "record.json"
        self.apk = Path(self.tmp.name) / "app.apk"
        with zipfile.ZipFile(self.apk, "w") as package:
            package.writestr("AndroidManifest.xml", '<manifest package="app.orchard.tv"/>')
        self.tv = TV()
        self.identity = {"id": "unit-tv-1", "model": "TV-one", "brand": "test", "android": "14", "sdk": "34"}
        self.args = argparse.Namespace(apk=str(self.apk), flavor="standard", launcher_only=False,
                                       preview=False, original_home=None, uninstall=False, force_guard=False)

    def install(self):
        d.install(self.tv, self.args, self.identity, self.path)

    def restore(self):
        d.restore(self.tv, self.args, self.identity, self.path)

    def test_standard_install_retry_preserves_original_home_and_restores_explicit_component(self):
        self.install()
        original = self.path.read_bytes()
        self.assertEqual(d.expanded(self.tv.home()), d.expanded(d.HOME))
        self.install()
        self.assertEqual(original, self.path.read_bytes())
        self.restore()
        self.assertEqual("com.vendor.home/.Main", self.tv.home())
        self.assertEqual("restored", json.loads(self.path.read_text())["status"])

    def test_guard_restore_preserves_services_added_after_install(self):
        self.tv.refuse_takeover = True
        original = copy.deepcopy(self.tv.settings)
        self.install()
        self.assertTrue(self.tv.write_secure)
        self.tv.settings["enabled_accessibility_services"] += ":com.new.reader/.Service"
        self.tv.settings["enabled_notification_listeners"] += ":com.new.music/.Listener"
        self.restore()
        self.assertFalse(self.tv.write_secure)
        self.assertFalse(d.contains(self.tv.settings["enabled_accessibility_services"], d.GUARD))
        self.assertIn("com.reader.service/.Reader", self.tv.settings["enabled_accessibility_services"])
        self.assertIn("com.new.reader/.Service", self.tv.settings["enabled_accessibility_services"])
        self.assertIn("com.new.music/.Listener", self.tv.settings["enabled_notification_listeners"])
        self.assertIn(original["enabled_notification_listeners"], self.tv.settings["enabled_notification_listeners"])

    def test_preview_and_launcher_only_never_grant_takeover(self):
        self.args.preview = True
        self.install()
        self.assertEqual([], self.tv.mutations)
        self.assertFalse(self.path.exists())
        self.args.preview = False
        self.args.launcher_only = True
        self.install()
        self.assertEqual([("install",)], self.tv.mutations)
        self.assertFalse(self.path.exists())

    def test_no_record_and_different_device_are_refused_before_mutation(self):
        with self.assertRaisesRegex(ValueError, "No recovery record"):
            self.restore()
        self.assertEqual([], self.tv.mutations)
        d.prepare_record(self.tv, self.identity, self.path)
        other = dict(self.identity, id="another-tv")
        with self.assertRaisesRegex(ValueError, "different TV"):
            d.restore(self.tv, self.args, other, self.path)
        self.assertEqual([], self.tv.mutations)

    def test_corrupt_record_cannot_be_overwritten_or_replayed(self):
        self.path.write_text('{"version": 99}')
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            self.install()
        with self.assertRaises(ValueError):
            self.restore()
        self.assertEqual(before, self.path.read_bytes())
        self.assertEqual([], self.tv.mutations)

    def test_home_restore_failure_does_not_claim_success_or_discard_record(self):
        self.install()
        self.tv.fail_home = True
        with self.assertRaisesRegex(RuntimeError, "Recovery incomplete"):
            self.restore()
        self.assertEqual("active", json.loads(self.path.read_text())["status"])

    def test_preexisting_permissions_and_appops_are_preserved(self):
        self.tv.installed = True
        self.tv.write_secure = True
        self.tv.ops["WRITE_SETTINGS"] = "allow"
        self.tv.ops["SYSTEM_ALERT_WINDOW"] = "ignore"
        self.install()
        self.tv.ops["WRITE_SETTINGS"] = "deny"
        self.restore()
        self.assertTrue(self.tv.write_secure)
        self.assertEqual("allow", self.tv.ops["WRITE_SETTINGS"])
        self.assertEqual("ignore", self.tv.ops["SYSTEM_ALERT_WINDOW"])

    def test_preexisting_app_data_cannot_be_uninstalled_by_restore(self):
        self.tv.installed = True
        self.install()
        self.args.uninstall = True
        count = len(self.tv.mutations)
        with self.assertRaisesRegex(ValueError, "existing data"):
            self.restore()
        self.assertEqual(count, len(self.tv.mutations))

    def test_same_model_at_different_ip_uses_stable_id(self):
        directory = Path(self.tmp.name)
        self.assertEqual(d.record_path(directory, self.identity), d.record_path(directory, dict(self.identity)))
        self.assertNotEqual(d.record_path(directory, self.identity), d.record_path(directory, dict(self.identity, id="other")))

    def test_failed_apk_install_still_has_usable_recovery_without_package_permissions(self):
        self.tv.fail_install = True
        with self.assertRaisesRegex(RuntimeError, "INCOMPATIBLE"):
            self.install()
        self.assertTrue(self.path.exists())
        self.restore()
        self.assertEqual("com.vendor.home/.Main", self.tv.home())
        self.assertFalse(self.tv.installed)

    def test_unknown_original_home_prevents_install_and_backup(self):
        self.tv.home_component = d.HOME
        with self.assertRaisesRegex(ValueError, "original launcher"):
            self.install()
        self.assertFalse(self.path.exists())
        self.assertEqual([], self.tv.mutations)

    def test_wrong_apk_is_refused_before_install_or_snapshot(self):
        with zipfile.ZipFile(self.apk, "w") as package:
            package.writestr("AndroidManifest.xml", '<manifest package="com.other.app"/>')
        with self.assertRaisesRegex(ValueError, "expected launcher package"):
            self.install()
        self.assertFalse(self.path.exists())
        self.assertEqual([], self.tv.mutations)

    def test_accessibility_global_switch_is_restored_without_disabling_new_services(self):
        self.tv.refuse_takeover = True
        self.tv.settings["enabled_accessibility_services"] = "null"
        self.tv.settings["accessibility_enabled"] = "0"
        self.install()
        self.restore()
        self.assertEqual("0", self.tv.settings["accessibility_enabled"])

    def test_new_service_keeps_accessibility_enabled(self):
        self.tv.refuse_takeover = True
        self.tv.settings["enabled_accessibility_services"] = "null"
        self.tv.settings["accessibility_enabled"] = "0"
        self.install()
        self.tv.settings["enabled_accessibility_services"] += ":com.new.reader/.Service"
        self.restore()
        self.assertEqual("1", self.tv.settings["accessibility_enabled"])

    def test_completed_recovery_is_idempotent_and_next_install_records_new_baseline(self):
        self.install()
        self.restore()
        count = len(self.tv.mutations)
        self.restore()
        self.assertEqual(count, len(self.tv.mutations))
        self.tv.home_component = "com.other.home/.Launcher"
        self.install()
        self.assertEqual("com.other.home/.Launcher", json.loads(self.path.read_text())["home"])
        self.assertEqual(1, len(list(Path(self.tmp.name).glob("*.restored.json"))))


if __name__ == "__main__":
    unittest.main()

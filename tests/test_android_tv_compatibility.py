import os
import shutil
import tempfile
import unittest
from pathlib import Path
from PIL import Image

from web2apk.template_engine import TemplateEngine
from web2apk.code_patcher import CodePatcher


class TestAndroidTvCompatibility(unittest.TestCase):

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="web2apk_tv_compat_test_"))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_tv_manifest_hardware_features_and_leanback_banner(self):
        manifest_xml = TemplateEngine._get_manifest(
            package_name="com.test.tvapp",
            app_name="Test TV App",
            is_tv=True,
            orientation="sensor",
            extra_permissions=[]
        )

        # 1. Hardware features marked required="false"
        self.assertIn('<uses-feature android:name="android.software.leanback" android:required="false"', manifest_xml)
        self.assertIn('<uses-feature android:name="android.hardware.touchscreen" android:required="false"', manifest_xml)
        self.assertIn('<uses-feature android:name="android.hardware.location" android:required="false"', manifest_xml)
        self.assertIn('<uses-feature android:name="android.hardware.location.gps" android:required="false"', manifest_xml)
        self.assertIn('<uses-feature android:name="android.hardware.telephony" android:required="false"', manifest_xml)
        self.assertIn('<uses-feature android:name="android.hardware.camera" android:required="false"', manifest_xml)
        self.assertIn('<uses-feature android:name="android.hardware.wifi" android:required="false"', manifest_xml)

        # 2. android:banner declared on <application> AND <activity>
        app_tag_idx = manifest_xml.find('<application')
        activity_tag_idx = manifest_xml.find('<activity')
        self.assertGreater(app_tag_idx, -1)
        self.assertGreater(activity_tag_idx, -1)

        app_chunk = manifest_xml[app_tag_idx:activity_tag_idx]
        activity_chunk = manifest_xml[activity_tag_idx:]
        self.assertIn('android:banner="@drawable/tv_banner"', app_chunk)
        self.assertIn('android:banner="@drawable/tv_banner"', activity_chunk)

        # 3. Dual separate intent-filters for LEANBACK_LAUNCHER and standard LAUNCHER
        self.assertIn('android.intent.category.LEANBACK_LAUNCHER', manifest_xml)
        self.assertIn('android.intent.category.LAUNCHER', manifest_xml)
        self.assertGreaterEqual(manifest_xml.count('<intent-filter>'), 2)

        # 4. Landscape orientation enforced for TV
        self.assertIn('android:screenOrientation="landscape"', manifest_xml)

    def test_main_activity_dispatch_key_event_and_tv_detection(self):
        activity_java = TemplateEngine._get_main_activity(
            package_name="com.test.tvapp",
            is_fullscreen=True,
            remote_url=None,
            is_tv=True,
            theme_color="#0f172a"
        )

        # 1. dispatchKeyEvent intercepts TV remote D-Pad events before WebView consumes them
        self.assertIn("public boolean dispatchKeyEvent(KeyEvent event)", activity_java)
        self.assertIn("KeyEvent.KEYCODE_DPAD_UP", activity_java)
        self.assertIn("KeyEvent.KEYCODE_DPAD_DOWN", activity_java)
        self.assertIn("KeyEvent.KEYCODE_DPAD_LEFT", activity_java)
        self.assertIn("KeyEvent.KEYCODE_DPAD_RIGHT", activity_java)
        self.assertIn("KeyEvent.KEYCODE_DPAD_CENTER", activity_java)
        self.assertIn("KeyEvent.KEYCODE_ENTER", activity_java)

        # 2. Unconditional true return for checkIsTvDevice when is_tv=True
        self.assertIn("if (true)", activity_java)
        self.assertIn("return true;", activity_java)

        # 3. Virtual mouse bringToFront & VISIBLE on initialization
        self.assertIn("tvMouseContainer.bringToFront()", activity_java)
        self.assertIn("tvMouseContainer.setVisibility(View.VISIBLE)", activity_java)

        # 4. Local coordinate calculation for click accuracy
        self.assertIn("webView.getLocationOnScreen(loc)", activity_java)
        self.assertIn("final float targetX = Math.max(0, cursorX - loc[0]);", activity_java)

    def test_cursor_png_fallback_generation(self):
        res_dir = self.temp_dir / "res"
        TemplateEngine._generate_res_files(res_dir, "Test App")

        xml_cursor = res_dir / "drawable" / "ic_tv_mouse_cursor.xml"
        self.assertTrue(xml_cursor.exists(), "ic_tv_mouse_cursor.xml was not created")

        png_cursor = res_dir / "drawable-xhdpi" / "ic_tv_mouse_cursor.png"
        self.assertTrue(png_cursor.exists(), "ic_tv_mouse_cursor.png was not created in drawable-xhdpi")

        with Image.open(png_cursor) as img:
            self.assertEqual(img.size, (48, 48))
            self.assertEqual(img.mode, "RGBA")

    def test_tv_spatial_navigation_injected_into_html(self):
        web_dir = self.temp_dir / "web"
        web_dir.mkdir(parents=True, exist_ok=True)
        (web_dir / "index.html").write_text("""<!DOCTYPE html>
<html>
<head><title>Test TV</title></head>
<body>
    <button id="btn1">Button 1</button>
    <button id="btn2">Button 2</button>
</body>
</html>""", encoding="utf-8")

        res = CodePatcher.patch_html_directory(str(web_dir), enable_tv_nav=True)
        self.assertTrue(res["success"])

        tv_nav_js = web_dir / "web2apk-tv-nav.js"
        self.assertTrue(tv_nav_js.exists(), "web2apk-tv-nav.js was not written")

        patched_html = (web_dir / "index.html").read_text(encoding="utf-8")
        self.assertIn("web2apk-tv-nav.js", patched_html)


if __name__ == "__main__":
    unittest.main()

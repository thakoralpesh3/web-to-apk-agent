import os
import shutil
import tempfile
import unittest
from pathlib import Path

from web2apk.template_engine import TemplateEngine
from web2apk.code_patcher import TV_DPAD_NAV_JS
from web2apk.builder import APKBuilder

class TestAndroidTVMousePointer(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_mouse_cursor_drawables_and_layout(self):
        """Verify ic_tv_mouse_cursor.xml, tv_mouse_click_ring.xml, and activity_main.xml have cursor elements."""
        proj_dir = TemplateEngine.generate_project(
            target_dir=os.path.join(self.temp_dir, "test_proj_res"),
            app_name="TV Mouse App",
            package_name="com.tv.mouseapp",
            is_tv_compatible=True
        )

        res_dir = Path(proj_dir) / "app" / "src" / "main" / "res"
        cursor_xml = res_dir / "drawable" / "ic_tv_mouse_cursor.xml"
        ring_xml = res_dir / "drawable" / "tv_mouse_click_ring.xml"
        layout_xml = res_dir / "layout" / "activity_main.xml"

        self.assertTrue(cursor_xml.exists(), "ic_tv_mouse_cursor.xml should exist in res/drawable")
        self.assertTrue(ring_xml.exists(), "tv_mouse_click_ring.xml should exist in res/drawable")
        self.assertTrue(layout_xml.exists(), "activity_main.xml should exist in res/layout")

        cursor_content = cursor_xml.read_text(encoding="utf-8")
        self.assertIn("<vector", cursor_content)
        self.assertIn("#FFFFFF", cursor_content)

        layout_content = layout_xml.read_text(encoding="utf-8")
        self.assertIn("tvMouseContainer", layout_content)
        self.assertIn("tvMouseClickRing", layout_content)
        self.assertIn("tvMouseCursor", layout_content)
        self.assertIn("@drawable/ic_tv_mouse_cursor", layout_content)

    def test_main_activity_virtual_mouse_engine(self):
        """Verify MainActivity.java has complete virtual mouse pointer logic for Android TV."""
        proj_dir = TemplateEngine.generate_project(
            target_dir=os.path.join(self.temp_dir, "test_proj_java"),
            app_name="TV Mouse Java App",
            package_name="com.tv.mousejava",
            is_tv_compatible=True
        )

        main_activity_path = Path(proj_dir) / "app" / "src" / "main" / "java" / "com" / "tv" / "mousejava" / "MainActivity.java"
        self.assertTrue(main_activity_path.exists())
        java_code = main_activity_path.read_text(encoding="utf-8")

        # Fields & Views
        self.assertIn("private FrameLayout tvMouseContainer", java_code)
        self.assertIn("private ImageView tvMouseCursor", java_code)
        self.assertIn("private View tvMouseClickRing", java_code)
        self.assertIn("private boolean isMouseMode", java_code)
        self.assertIn("private boolean isTvDevice", java_code)

        # Engine Methods
        self.assertIn("initVirtualMouse()", java_code)
        self.assertIn("checkIsTvDevice()", java_code)
        self.assertIn("moveMouseCursor", java_code)
        self.assertIn("performMouseClick()", java_code)
        self.assertIn("dispatchHover", java_code)
        self.assertIn("showMouseCursor()", java_code)
        self.assertIn("hideMouseCursor()", java_code)

        # D-Pad Key Interceptions
        self.assertIn("case KeyEvent.KEYCODE_DPAD_UP:", java_code)
        self.assertIn("case KeyEvent.KEYCODE_DPAD_DOWN:", java_code)
        self.assertIn("case KeyEvent.KEYCODE_DPAD_LEFT:", java_code)
        self.assertIn("case KeyEvent.KEYCODE_DPAD_RIGHT:", java_code)
        self.assertIn("case KeyEvent.KEYCODE_DPAD_CENTER:", java_code)
        self.assertIn("case KeyEvent.KEYCODE_ENTER:", java_code)

        # Gamepad joystick motion
        self.assertIn("SOURCE_JOYSTICK", java_code)
        self.assertIn("AXIS_X", java_code)
        self.assertIn("AXIS_Y", java_code)

        # Smartphone touch hides cursor
        self.assertIn("hideMouseCursor()", java_code)

    def test_code_patcher_tv_cursor_styling(self):
        """Verify code_patcher.py does not suppress the mouse cursor."""
        self.assertNotIn("cursor: none;", TV_DPAD_NAV_JS)
        self.assertIn("cursor: default;", TV_DPAD_NAV_JS)

    def test_real_apk_compilation_with_mouse_cursor(self):
        """Compile a real Android TV compatible APK with virtual mouse cursor to ensure zero build errors."""
        web_dir = Path(self.temp_dir) / "web_tv_sample"
        web_dir.mkdir(parents=True, exist_ok=True)
        (web_dir / "index.html").write_text("""<!DOCTYPE html>
<html>
<head><title>TV Mouse Sample</title></head>
<body>
    <h1>Android TV Virtual Mouse Test</h1>
    <button id="btn1" onclick="alert('clicked')">Selectable Content</button>
</body>
</html>""")

        builder = APKBuilder()
        res = builder.build_from_directory(
            source_dir=str(web_dir),
            app_name="TV Mouse Suite",
            package_name="com.test.tvmousesuite",
            version_name="1.0.0",
            version_code=1,
            is_tv_compatible=True,
            is_fullscreen=True,
            screen_orientation="landscape"
        )
        self.assertTrue(res.get("success"), f"Build failed: {res.get('error')}")
        apk_path = res.get("apk_path")
        self.assertIsNotNone(apk_path)
        self.assertTrue(Path(apk_path).exists())

if __name__ == "__main__":
    unittest.main()

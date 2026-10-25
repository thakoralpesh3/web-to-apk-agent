import os
import shutil
import tempfile
import unittest
from pathlib import Path

from web2apk.template_engine import TemplateEngine
from web2apk.self_healer import SelfHealer, RUNTIME_HEALER_JS
from web2apk.code_patcher import CodePatcher


class TestBackNavigationAndLightsOut(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="web2apk_back_lights_test_"))

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_manifest_contains_predictive_back_callback(self):
        """Verifies AndroidManifest.xml includes enableOnBackInvokedCallback for Android 13+ support."""
        project_dir = self.test_dir / "project"
        TemplateEngine.generate_project(
            target_dir=str(project_dir),
            app_name="CinemaStream",
            package_name="com.cinemastream.app",
            version_code=1,
            version_name="1.0.0",
            is_fullscreen=True,
            remote_url="https://cinemastream.example.com",
            is_tv_compatible=True,
            screen_orientation="sensor"
        )

        manifest_file = project_dir / "app/src/main/AndroidManifest.xml"
        self.assertTrue(manifest_file.exists())
        manifest_xml = manifest_file.read_text(encoding="utf-8")
        self.assertIn('android:enableOnBackInvokedCallback="true"', manifest_xml)

    def test_main_activity_back_navigation_architecture(self):
        """Verifies MainActivity.java implements robust back navigation across all Android versions."""
        project_dir = self.test_dir / "project"
        TemplateEngine.generate_project(
            target_dir=str(project_dir),
            app_name="CinemaStream",
            package_name="com.cinemastream.app",
            version_code=1,
            version_name="1.0.0",
            is_fullscreen=False,
            remote_url="https://cinemastream.example.com",
            is_tv_compatible=True,
            screen_orientation="sensor"
        )

        activity_file = project_dir / "app/src/main/java/com/cinemastream/app/MainActivity.java"
        self.assertTrue(activity_file.exists())
        src = activity_file.read_text(encoding="utf-8")

        # 1. Verify Imports
        self.assertIn("import android.window.OnBackInvokedCallback;", src)
        self.assertIn("import android.window.OnBackInvokedDispatcher;", src)
        self.assertIn("import android.webkit.WebBackForwardList;", src)
        self.assertIn("import android.webkit.WebHistoryItem;", src)

        # 2. Verify Android 13+ Callback Registration
        self.assertIn("registerBackInvokedCallback()", src)
        self.assertIn("getOnBackInvokedDispatcher().registerOnBackInvokedCallback", src)

        # 3. Verify Key Handling Interception
        self.assertIn("dispatchKeyEvent(KeyEvent event)", src)
        self.assertIn("keyCode == KeyEvent.KEYCODE_BACK", src)
        self.assertIn("onKeyDown(int keyCode, KeyEvent event)", src)
        self.assertIn("onBackPressed()", src)

        # 4. Verify Unified handleBackPress and standard back navigation
        self.assertIn("public void handleBackPress()", src)
        self.assertIn("proceedWithStandardBackNavigation()", src)
        self.assertIn("webView.canGoBack()", src)
        self.assertIn("webView.goBack()", src)
        self.assertIn("Press back again to exit", src)

        # 5. Verify Lights Out Bridge on WebAppInterface
        self.assertIn("setLightsOutActive(boolean active)", src)
        self.assertIn("isLightsOutActive()", src)
        self.assertIn("dismissLightsOutOrModal", src)

        # 6. Verify onPageFinished Video Elevation & Lights Out Injection
        self.assertIn("web2apk-injected-lights-css", src)
        self.assertIn("2147483640 !important", src)
        self.assertIn("initLightsOutHealer", src)

    def test_bridge_js_contains_lights_out_healer(self):
        """Verifies web2apk-bridge.js contains lights-out dismissal, video elevation, and floating button."""
        bridge_file = Path(__file__).resolve().parent.parent / "web2apk" / "assets" / "web2apk-bridge.js"
        self.assertTrue(bridge_file.exists())
        src = bridge_file.read_text(encoding="utf-8")

        self.assertIn("dismissLightsOutOrModal()", src)
        self.assertIn("initLightsOutHealer()", src)
        self.assertIn("setLightsOutActive", src)
        self.assertIn("isLightsOutActive", src)
        self.assertIn("web2apk-lights-out-btn", src)
        self.assertIn("Turn On Lights", src)
        self.assertIn("keyCode: 27", src)
        self.assertIn("2147483640 !important", src)
        self.assertIn("window.__web2apk_dismissLightsOut", src)

    def test_runtime_healer_js_contains_lights_out_protection(self):
        """Verifies RUNTIME_HEALER_JS prevents blank screen and elevates videos."""
        self.assertIn("web2apk-lights-out-btn", RUNTIME_HEALER_JS)
        self.assertIn("Turn On Lights", RUNTIME_HEALER_JS)
        self.assertIn("2147483640 !important", RUNTIME_HEALER_JS)
        self.assertIn("window.__web2apk_dismissLightsOut", RUNTIME_HEALER_JS)

    def test_self_healer_diagnose_and_heal_directory_injects_lights_fix(self):
        """Verifies SelfHealer.diagnose_and_heal_directory injects the updated runtime healer."""
        web_dir = self.test_dir / "web_site"
        web_dir.mkdir(parents=True)
        (web_dir / "index.html").write_text("""<!DOCTYPE html>
<html>
<head><title>Streaming Site</title></head>
<body>
    <div id="player-container">
        <video id="vid" controls src="video.mp4"></video>
    </div>
    <button id="lights-btn" onclick="document.body.classList.toggle('lights-off')">Lights Out</button>
</body>
</html>""", encoding="utf-8")

        result = SelfHealer.diagnose_and_heal_directory(web_dir)
        self.assertTrue(result["success"])

        healer_file = web_dir / "web2apk-runtime-healer.js"
        self.assertTrue(healer_file.exists())
        content = healer_file.read_text(encoding="utf-8")
        self.assertIn("web2apk-lights-out-btn", content)
        self.assertIn("2147483640 !important", content)


if __name__ == "__main__":
    unittest.main()

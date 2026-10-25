import os
import shutil
import tempfile
import unittest
from pathlib import Path

from web2apk.template_engine import TemplateEngine
from web2apk.builder import APKBuilder


class TestEssentialFeatures(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="web2apk_essential_test_"))

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_essential_features_in_manifest_and_activity(self):
        project_dir = self.test_dir / "project"
        TemplateEngine.generate_project(
            target_dir=str(project_dir),
            app_name="SuperApp",
            package_name="com.superapp.pro",
            version_code=1,
            version_name="1.0.0",
            is_fullscreen=False,
            remote_url="https://superapp.example.com",
            is_tv_compatible=True,
            screen_orientation="sensor"
        )

        manifest_file = project_dir / "app/src/main/AndroidManifest.xml"
        self.assertTrue(manifest_file.exists())
        manifest_xml = manifest_file.read_text(encoding="utf-8")

        # 1. Verify Manifest permissions & Picture-in-Picture
        self.assertIn("android:supportsPictureInPicture=\"true\"", manifest_xml)
        self.assertIn("android.permission.WRITE_EXTERNAL_STORAGE", manifest_xml)
        self.assertIn("android.permission.ACCESS_FINE_LOCATION", manifest_xml)
        self.assertIn("android.permission.ACCESS_COARSE_LOCATION", manifest_xml)

        activity_file = project_dir / "app/src/main/java/com/superapp/pro/MainActivity.java"
        self.assertTrue(activity_file.exists())
        activity_src = activity_file.read_text(encoding="utf-8")

        # 2. Verify File Download Manager
        self.assertIn("setDownloadListener", activity_src)
        self.assertIn("DownloadManager.Request", activity_src)
        self.assertIn("URLUtil.guessFileName", activity_src)
        self.assertIn("Environment.DIRECTORY_DOWNLOADS", activity_src)

        # 3. Verify Geolocation API
        self.assertIn("onGeolocationPermissionsShowPrompt", activity_src)
        self.assertIn("setGeolocationEnabled(true)", activity_src)
        self.assertIn("PERMISSIONS_REQUEST_LOCATION", activity_src)

        # 4. Verify Cookie Persistence & Third-Party Cookies
        self.assertIn("setAcceptThirdPartyCookies", activity_src)
        self.assertIn("CookieManager.getInstance().flush()", activity_src)

        # 5. Verify Multi-Window / OAuth Popup
        self.assertIn("setSupportMultipleWindows(true)", activity_src)
        self.assertIn("onCreateWindow", activity_src)

        # 6. Verify Intent Scheme & Deep Linking
        self.assertIn("Intent.parseUri", activity_src)
        self.assertIn("browser_fallback_url", activity_src)

        # 7. Verify Picture-in-Picture & Activity Lifecycle
        self.assertIn("enterPictureInPictureMode", activity_src)
        self.assertIn("onUserLeaveHint", activity_src)
        self.assertIn("onPause", activity_src)
        self.assertIn("onResume", activity_src)
        self.assertIn("onDestroy", activity_src)

        # 8. Verify Zoom controls
        self.assertIn("setSupportZoom(true)", activity_src)
        self.assertIn("setBuiltInZoomControls(true)", activity_src)

    def test_end_to_end_apk_build_with_essential_features(self):
        web_dir = self.test_dir / "web_app"
        web_dir.mkdir(parents=True)
        (web_dir / "index.html").write_text("""<!DOCTYPE html>
<html>
<head><title>Super App Feature Test</title></head>
<body>
    <h1>Feature Rich Web App</h1>
    <a href="sample.pdf" download>Download PDF Document</a>
    <button onclick="navigator.geolocation.getCurrentPosition(()=>{})">Locate Me</button>
    <a href="intent://example.com#Intent;scheme=https;end">Open in App</a>
</body>
</html>""", encoding="utf-8")

        builder = APKBuilder()
        build_result = builder.build_from_directory(
            source_dir=str(web_dir),
            package_name="com.superapp.features",
            app_name="SuperApp Features",
            version_code=1,
            version_name="1.0.0"
        )

        self.assertTrue(build_result.get("success", False), f"Build failed: {build_result.get('error')}")
        apk_path = Path(build_result.get("apk_path", ""))
        self.assertTrue(apk_path.exists())
        self.assertGreater(apk_path.stat().st_size, 5000)


if __name__ == "__main__":
    unittest.main()

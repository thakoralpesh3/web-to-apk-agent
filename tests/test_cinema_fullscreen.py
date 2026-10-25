import os
import shutil
import tempfile
import unittest
from pathlib import Path

from web2apk.template_engine import TemplateEngine
from web2apk.code_patcher import CodePatcher
from web2apk.builder import APKBuilder


class TestCinemaFullscreen(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="web2apk_cinema_test_"))

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_template_layout_and_activity_contain_fullscreen_components(self):
        project_dir = self.test_dir / "project"
        res = TemplateEngine.generate_project(
            target_dir=str(project_dir),
            app_name="CinemaStreamApp",
            package_name="com.cinema.streamapp",
            version_code=1,
            version_name="1.0.0",
            is_fullscreen=True,
            remote_url="https://cinema.example.com",
            is_tv_compatible=True,
            screen_orientation="sensor"
        )

        layout_file = project_dir / "app/src/main/res/layout/activity_main.xml"
        self.assertTrue(layout_file.exists(), "activity_main.xml must be generated")
        layout_xml = layout_file.read_text(encoding="utf-8")
        self.assertIn('android:id="@+id/customViewContainer"', layout_xml)
        self.assertIn('android:visibility="gone"', layout_xml)
        self.assertIn('android:id="@+id/webview"', layout_xml)

        activity_file = project_dir / "app/src/main/java/com/cinema/streamapp/MainActivity.java"
        self.assertTrue(activity_file.exists(), "MainActivity.java must be generated")
        activity_src = activity_file.read_text(encoding="utf-8")

        # Verify CustomView & Fullscreen WebChromeClient methods
        self.assertIn("customViewContainer", activity_src)
        self.assertIn("onShowCustomView", activity_src)
        self.assertIn("onHideCustomView", activity_src)
        self.assertIn("SCREEN_ORIENTATION_SENSOR_LANDSCAPE", activity_src)
        self.assertIn("SYSTEM_UI_FLAG_IMMERSIVE_STICKY", activity_src)

        # Verify Back button handling
        self.assertIn("onKeyDown", activity_src)
        self.assertIn("onBackPressed", activity_src)
        self.assertIn("webChromeClient.onHideCustomView()", activity_src)

        # Verify Media / DRM permissions
        self.assertIn("onPermissionRequest", activity_src)
        self.assertIn("request.grant", activity_src)

        # Verify Posters & Progress
        self.assertIn("getDefaultVideoPoster", activity_src)
        self.assertIn("getVideoLoadingProgressView", activity_src)

        # Verify Mixed content and User-Agent optimization for streaming
        self.assertIn("MIXED_CONTENT_ALWAYS_ALLOW", activity_src)
        self.assertIn('replace("; wv", "")', activity_src)

        # Verify Iframe permissions injection
        self.assertIn("allowfullscreen", activity_src)
        self.assertIn("picture-in-picture", activity_src)

    def test_code_patcher_patches_cinema_iframes(self):
        html_content = """<!DOCTYPE html>
<html>
<head><title>Cinema Player</title></head>
<body>
    <h1>Now Playing</h1>
    <iframe src="https://player.vimeo.com/video/76979871" width="640" height="360"></iframe>
    <iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ" allow="accelerometer; clipboard-write"></iframe>
</body>
</html>"""
        html_file = self.test_dir / "index.html"
        html_file.write_text(html_content, encoding="utf-8")

        res = CodePatcher.patch_directory(self.test_dir, app_title="Cinema Player")
        self.assertTrue(res["success"])
        self.assertGreaterEqual(res["stats"]["iframes_patched"], 2)

        patched_content = html_file.read_text(encoding="utf-8")
        self.assertIn('allowfullscreen="true"', patched_content)
        self.assertIn('allow="autoplay; fullscreen; encrypted-media; picture-in-picture"', patched_content)
        # Verify second iframe merged permissions
        self.assertIn('accelerometer', patched_content)
        self.assertIn('fullscreen', patched_content)

    def test_end_to_end_cinema_apk_compilation(self):
        # Create a sample cinema web application
        web_dir = self.test_dir / "cinema_web"
        web_dir.mkdir(parents=True)
        (web_dir / "index.html").write_text("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Cinema Box Office</title>
</head>
<body style="background: #000; color: #fff; font-family: sans-serif; text-align: center;">
    <h2>Cinema Box Office Stream</h2>
    <video controls width="100%">
        <source src="trailer.mp4" type="video/mp4">
    </video>
    <iframe src="https://example.com/embed/movie123" width="100%" height="300"></iframe>
</body>
</html>""", encoding="utf-8")

        builder = APKBuilder()
        build_result = builder.build_from_directory(
            source_dir=str(web_dir),
            package_name="com.cinema.moviebox",
            app_name="Cinema MovieBox",
            version_code=1,
            version_name="1.0.0",
            screen_orientation="sensor",
            is_fullscreen=True,
            is_tv_compatible=True
        )

        self.assertTrue(build_result.get("success", False), f"Build failed: {build_result.get('error')}")
        apk_path = Path(build_result.get("apk_path", ""))
        self.assertTrue(apk_path.exists(), f"Output APK should exist at {apk_path}")
        self.assertGreater(apk_path.stat().st_size, 5000, "APK file size should be > 5KB")


if __name__ == "__main__":
    unittest.main()

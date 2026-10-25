import os
import shutil
import tempfile
import unittest
from pathlib import Path
from PIL import Image

from web2apk.icon_generator import IconGenerator
from web2apk.app_inspector import AppInspector
from web2apk.builder import APKBuilder


SAMPLE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
    <rect width="200" height="200" rx="40" fill="#6366f1"/>
    <circle cx="100" cy="100" r="60" fill="#38bdf8"/>
    <polygon points="85,70 135,100 85,130" fill="#ffffff"/>
</svg>"""

SAMPLE_SVG_INLINE = """<!DOCTYPE html>
<html>
<head><title>Vector Movie App</title></head>
<body>
    <header>
        <svg class="site-logo" viewBox="0 0 120 120" width="120" height="120">
            <rect width="120" height="120" rx="20" fill="#e11d48"/>
            <text x="60" y="75" font-size="50" text-anchor="middle" fill="#ffffff">M</text>
        </svg>
        <h1>Movie Central</h1>
    </header>
</body>
</html>"""


class TestLogoAutoselectionAndOverride(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="web2apk_logo_test_"))

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_icon_generator_rasterizes_svg_file(self):
        svg_file = self.test_dir / "logo.svg"
        svg_file.write_text(SAMPLE_SVG, encoding="utf-8")

        norm_img = IconGenerator.load_and_normalize_image(str(svg_file), 512, "TestApp")
        self.assertIsInstance(norm_img, Image.Image)
        self.assertEqual(norm_img.width, 512)
        self.assertEqual(norm_img.height, 512)
        self.assertEqual(norm_img.mode, "RGBA")

    def test_icon_generator_handles_data_uri_svg(self):
        data_uri = "data:image/svg+xml;utf8," + SAMPLE_SVG.replace("\n", "").replace(" ", "%20")
        norm_img = IconGenerator.load_and_normalize_image(data_uri, 512, "DataUriApp")
        self.assertIsInstance(norm_img, Image.Image)
        self.assertEqual(norm_img.width, 512)
        self.assertEqual(norm_img.height, 512)

    def test_autoselect_svg_from_project_directory(self):
        project_dir = self.test_dir / "my_web_project"
        project_dir.mkdir()
        (project_dir / "index.html").write_text("<!DOCTYPE html><html><head><title>Cinema App</title></head><body>Cinema</body></html>")
        (project_dir / "logo.svg").write_text(SAMPLE_SVG, encoding="utf-8")

        blueprint = AppInspector.inspect_directory(project_dir)
        self.assertIsNotNone(blueprint.get("icon_path"))
        self.assertTrue(Path(blueprint["icon_path"]).exists())
        self.assertIsNotNone(blueprint.get("icon_base64"))
        self.assertTrue(blueprint["icon_base64"].startswith("data:image/png;base64,"))

        # Check normalized image dimensions
        with Image.open(blueprint["icon_path"]) as img:
            self.assertEqual(img.size, (512, 512))

    def test_autoselect_inline_svg_from_html(self):
        project_dir = self.test_dir / "inline_svg_project"
        project_dir.mkdir()
        (project_dir / "index.html").write_text(SAMPLE_SVG_INLINE, encoding="utf-8")

        blueprint = AppInspector.inspect_directory(project_dir)
        self.assertIsNotNone(blueprint.get("icon_path"))
        self.assertTrue(Path(blueprint["icon_path"]).exists())

        with Image.open(blueprint["icon_path"]) as img:
            self.assertEqual(img.size, (512, 512))

    def test_autoselect_manifest_svg_icon(self):
        project_dir = self.test_dir / "manifest_svg_project"
        project_dir.mkdir()
        assets_dir = project_dir / "assets"
        assets_dir.mkdir()
        (assets_dir / "app_icon.svg").write_text(SAMPLE_SVG, encoding="utf-8")

        manifest_content = """{
            "name": "Manifest SVG App",
            "icons": [
                {
                    "src": "assets/app_icon.svg",
                    "type": "image/svg+xml",
                    "sizes": "any"
                }
            ]
        }"""
        (project_dir / "manifest.json").write_text(manifest_content, encoding="utf-8")
        (project_dir / "index.html").write_text("<html><head><title>Manifest App</title></head><body>App</body></html>")

        blueprint = AppInspector.inspect_directory(project_dir)
        self.assertEqual(blueprint["app_name"], "Manifest SVG App")
        self.assertIsNotNone(blueprint.get("icon_path"))
        self.assertTrue(Path(blueprint["icon_path"]).exists())

    def test_manual_override_with_custom_svg_icon(self):
        # Build an APK where the user explicitly overrides the icon with an SVG
        web_dir = self.test_dir / "simple_web"
        web_dir.mkdir()
        (web_dir / "index.html").write_text("<html><head><title>Manual Override</title></head><body>App</body></html>")

        custom_svg = self.test_dir / "custom_user_logo.svg"
        custom_svg.write_text(SAMPLE_SVG, encoding="utf-8")

        builder = APKBuilder()
        build_result = builder.build_from_directory(
            source_dir=str(web_dir),
            app_name="Manual SVG Brand",
            package_name="com.manual.svgbrand",
            icon_path=str(custom_svg),
            version_code=1,
            version_name="1.0.0"
        )

        self.assertTrue(build_result.get("success", False), f"Build failed: {build_result.get('error')}")
        apk_path = Path(build_result.get("apk_path", ""))
        self.assertTrue(apk_path.exists())
        self.assertGreater(apk_path.stat().st_size, 5000)


if __name__ == "__main__":
    unittest.main()

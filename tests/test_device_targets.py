import os
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from fastapi.testclient import TestClient

from web2apk.builder import APKBuilder, OUTPUT_DIR
from web2apk.qr_server import QRServer
from web2apk.gui.server import app


class TestDeviceTargets(unittest.TestCase):

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="web2apk_target_test_"))
        self.created_apks = []

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        for apk_path in self.created_apks:
            if apk_path and Path(apk_path).exists():
                try:
                    Path(apk_path).unlink()
                except Exception:
                    pass

    def _create_sample_web_dir(self, name: str = "TestApp") -> Path:
        web_dir = self.temp_dir / f"web_{name}"
        web_dir.mkdir(parents=True, exist_ok=True)
        (web_dir / "index.html").write_text(f"""<!DOCTYPE html>
<html>
<head><title>{name}</title></head>
<body>
    <h1>Hello {name}</h1>
    <p>Target Device Architecture Test</p>
</body>
</html>""", encoding="utf-8")
        return web_dir

    def test_build_smartphone_target(self):
        web_dir = self._create_sample_web_dir("PhoneOnly")
        builder = APKBuilder()
        res = builder.build_from_directory(
            source_dir=str(web_dir),
            app_name="Phone Only App",
            package_name="com.test.phoneonly",
            version_name="1.0.0",
            target_device="smartphone"
        )
        self.assertTrue(res.get("success"), f"Build failed: {res.get('error')}")
        self.assertEqual(res.get("target_device"), "smartphone")
        self.assertFalse(res.get("tv_compatible"))
        
        phone_apk = res.get("smartphone_apk_name")
        self.assertIsNotNone(phone_apk)
        self.assertTrue(phone_apk.endswith("-smartphone.apk"))
        self.assertIsNone(res.get("tv_apk_name"))

        full_path = Path(res["apk_path"])
        self.assertTrue(full_path.exists())
        self.created_apks.append(str(full_path))
        self.created_apks.append(res.get("smartphone_apk_path"))

    def test_build_tv_target(self):
        web_dir = self._create_sample_web_dir("TVOnly")
        builder = APKBuilder()
        res = builder.build_from_directory(
            source_dir=str(web_dir),
            app_name="TV Only App",
            package_name="com.test.tvonly",
            version_name="1.0.0",
            target_device="tv"
        )
        self.assertTrue(res.get("success"), f"Build failed: {res.get('error')}")
        self.assertEqual(res.get("target_device"), "tv")
        self.assertTrue(res.get("tv_compatible"))

        tv_apk = res.get("tv_apk_name")
        self.assertIsNotNone(tv_apk)
        self.assertTrue(tv_apk.endswith("-android-tv.apk"))
        self.assertIsNone(res.get("smartphone_apk_name"))

        full_path = Path(res["apk_path"])
        self.assertTrue(full_path.exists())
        self.created_apks.append(str(full_path))
        self.created_apks.append(res.get("tv_apk_path"))

    def test_build_both_targets(self):
        web_dir = self._create_sample_web_dir("DualTarget")
        builder = APKBuilder()
        res = builder.build_from_directory(
            source_dir=str(web_dir),
            app_name="Dual Target App",
            package_name="com.test.dualtarget",
            version_name="1.0.0",
            target_device="both"
        )
        self.assertTrue(res.get("success"), f"Build failed: {res.get('error')}")
        self.assertEqual(res.get("target_device"), "both")

        phone_apk = res.get("smartphone_apk_name")
        tv_apk = res.get("tv_apk_name")
        self.assertIsNotNone(phone_apk, "Smartphone APK should be generated in dual mode")
        self.assertIsNotNone(tv_apk, "Android TV APK should be generated in dual mode")
        self.assertTrue(phone_apk.endswith("-smartphone.apk"))
        self.assertTrue(tv_apk.endswith("-android-tv.apk"))

        phone_path = Path(res["smartphone_apk_path"])
        tv_path = Path(res["tv_apk_path"])
        self.assertTrue(phone_path.exists())
        self.assertTrue(tv_path.exists())

        self.created_apks.extend([str(phone_path), str(tv_path), res.get("apk_path")])

    def test_qr_server_landing_page_renders_dual_buttons(self):
        app_stub = "TestDualLanding"
        phone_file = OUTPUT_DIR / f"{app_stub}-v1.0.0-smartphone.apk"
        tv_file = OUTPUT_DIR / f"{app_stub}-v1.0.0-android-tv.apk"

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        phone_file.write_bytes(b"PK000fakephone")
        tv_file.write_bytes(b"PK000faketv")

        self.created_apks.extend([str(phone_file), str(tv_file)])

        html = QRServer.generate_landing_page_html(phone_file.name, 1.5, "Test Dual Landing")
        self.assertIn("📱 Download for Android Phone", html)
        self.assertIn("📺 Download for Android TV", html)
        self.assertIn(f"{app_stub}-v1.0.0-smartphone.apk", html)
        self.assertIn(f"{app_stub}-v1.0.0-android-tv.apk", html)

    def test_api_build_smartphone_target(self):
        client = TestClient(app)
        web_dir = self._create_sample_web_dir("ApiPhone")
        
        zip_path = self.temp_dir / "sample_phone.zip"
        with zipfile.ZipFile(zip_path, "w") as z:
            z.write(web_dir / "index.html", arcname="index.html")

        with open(zip_path, "rb") as zf:
            response = client.post(
                "/api/build",
                data={
                    "mode": "zip",
                    "app_name": "API Phone App",
                    "package_name": "com.test.apiphone",
                    "version_name": "1.0.0",
                    "target_device": "smartphone"
                },
                files={"file": ("sample_phone.zip", zf, "application/zip")}
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"), f"API build failed: {data.get('error')}")
        self.assertEqual(data.get("target_device"), "smartphone")
        self.assertIsNotNone(data.get("smartphone_apk_name"))
        self.assertIsNone(data.get("tv_apk_name"))
        self.assertIn("smartphone_download_url", data)
        self.assertNotIn("tv_download_url", data)
        self.assertIn("smartphone_qr_code_base64", data)

        if data.get("apk_path"):
            self.created_apks.append(data["apk_path"])
        if data.get("smartphone_apk_path"):
            self.created_apks.append(data["smartphone_apk_path"])

    def test_api_build_tv_target(self):
        client = TestClient(app)
        web_dir = self._create_sample_web_dir("ApiTV")
        
        zip_path = self.temp_dir / "sample_tv.zip"
        with zipfile.ZipFile(zip_path, "w") as z:
            z.write(web_dir / "index.html", arcname="index.html")

        with open(zip_path, "rb") as zf:
            response = client.post(
                "/api/build",
                data={
                    "mode": "zip",
                    "app_name": "API TV App",
                    "package_name": "com.test.apitv",
                    "version_name": "1.0.0",
                    "target_device": "tv"
                },
                files={"file": ("sample_tv.zip", zf, "application/zip")}
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"), f"API build failed: {data.get('error')}")
        self.assertEqual(data.get("target_device"), "tv")
        self.assertIsNotNone(data.get("tv_apk_name"))
        self.assertIsNone(data.get("smartphone_apk_name"))
        self.assertIn("tv_download_url", data)
        self.assertNotIn("smartphone_download_url", data)
        self.assertIn("tv_qr_code_base64", data)

        if data.get("apk_path"):
            self.created_apks.append(data["apk_path"])
        if data.get("tv_apk_path"):
            self.created_apks.append(data["tv_apk_path"])


if __name__ == "__main__":
    unittest.main()

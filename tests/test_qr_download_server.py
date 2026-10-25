import os
import shutil
import tempfile
import urllib.request
import urllib.parse
import unittest
from pathlib import Path
from starlette.testclient import TestClient

from web2apk.qr_server import QRServer
from web2apk.gui.server import app, OUTPUT_DIR


class TestQRDownloadServer(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="web2apk_qr_test_"))
        self.dummy_apk_path = self.test_dir / "testapp-smartphone.apk"
        self.dummy_binary = b"PK\x03\x04FAKE_ANDROID_APK_BINARY_PAYLOAD_TEST_DATA_12345"
        with open(self.dummy_apk_path, "wb") as f:
            f.write(self.dummy_binary)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_local_ip_detection(self):
        ip = QRServer.get_local_ip()
        self.assertIsInstance(ip, str)
        self.assertTrue(len(ip) >= 7)
        # Should look like an IP address
        parts = ip.split(".")
        self.assertEqual(len(parts), 4)

    def test_download_url_generation(self):
        url = QRServer.get_download_url("demo-app.apk", port=8990)
        self.assertTrue(url.startswith("http://"))
        self.assertTrue(url.endswith("/download/demo-app.apk"))
        self.assertIn(":8990", url)

        custom_url = QRServer.get_download_url("demo-app.apk", host="http://192.168.1.100:5000")
        self.assertEqual(custom_url, "http://192.168.1.100:5000/download/demo-app.apk")

    def test_qr_base64_generation(self):
        b64 = QRServer.generate_qr_base64("http://192.168.1.50:8990/download/test.apk")
        self.assertTrue(b64.startswith("data:image/png;base64,"))
        self.assertTrue(len(b64) > 100)

    def test_landing_page_generation(self):
        html = QRServer.generate_landing_page_html(
            apk_name="cinema-stream-smartphone.apk",
            apk_size_mb=14.5,
            app_name="Cinema Stream Pro"
        )
        self.assertIn("Cinema Stream Pro", html)
        self.assertIn("14.5 MB", html)
        self.assertIn("/download-raw/cinema-stream-smartphone.apk", html)
        self.assertIn("How to Install on Android", html)

    def test_embedded_http_sideload_server(self):
        # Start embedded server in non-blocking thread
        server, port = QRServer.serve_apk(self.dummy_apk_path, port=18990, blocking=False)
        self.assertIsNotNone(server)
        self.assertTrue(port >= 18990)

        try:
            # 1. Request landing page
            landing_url = f"http://127.0.0.1:{port}/download/{self.dummy_apk_path.name}"
            req = urllib.request.Request(landing_url, headers={"User-Agent": "Mozilla/5.0 (Android; Mobile)"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                self.assertEqual(resp.status, 200)
                content_type = resp.headers.get("Content-Type", "")
                self.assertIn("text/html", content_type)
                body = resp.read().decode("utf-8")
                self.assertIn("testapp", body.lower())
                self.assertIn("/download-raw/", body)

            # 2. Request raw APK binary
            raw_url = f"http://127.0.0.1:{port}/download-raw/{self.dummy_apk_path.name}"
            with urllib.request.urlopen(raw_url, timeout=5) as resp:
                self.assertEqual(resp.status, 200)
                content_type = resp.headers.get("Content-Type", "")
                self.assertEqual(content_type, "application/vnd.android.package-archive")
                data = resp.read()
                self.assertEqual(data, self.dummy_binary)

            # 3. Request with ?raw=1 parameter
            param_raw_url = f"http://127.0.0.1:{port}/download/{self.dummy_apk_path.name}?raw=1"
            with urllib.request.urlopen(param_raw_url, timeout=5) as resp:
                self.assertEqual(resp.status, 200)
                content_type = resp.headers.get("Content-Type", "")
                self.assertEqual(content_type, "application/vnd.android.package-archive")
                data = resp.read()
                self.assertEqual(data, self.dummy_binary)

        finally:
            server.shutdown()
            server.server_close()

    def test_gui_server_download_endpoints(self):
        # Place test apk into OUTPUT_DIR
        test_out_apk = OUTPUT_DIR / "gui-test-app.apk"
        try:
            with open(test_out_apk, "wb") as f:
                f.write(self.dummy_binary)

            client = TestClient(app)

            # 1. Test landing page response
            resp = client.get("/download/gui-test-app.apk")
            self.assertEqual(resp.status_code, 200)
            self.assertIn("text/html", resp.headers["content-type"])
            self.assertIn("/download-raw/gui-test-app.apk", resp.text)

            # 2. Test raw binary download
            resp_raw = client.get("/download-raw/gui-test-app.apk")
            self.assertEqual(resp_raw.status_code, 200)
            self.assertEqual(resp_raw.headers["content-type"], "application/vnd.android.package-archive")
            self.assertEqual(resp_raw.content, self.dummy_binary)

            # 3. Test raw=1 query parameter
            resp_param = client.get("/download/gui-test-app.apk?raw=1")
            self.assertEqual(resp_param.status_code, 200)
            self.assertEqual(resp_param.headers["content-type"], "application/vnd.android.package-archive")
            self.assertEqual(resp_param.content, self.dummy_binary)

            # 4. Test QR code API
            resp_qr = client.get("/api/qr-code?url=http://10.0.0.5:8990/download/gui-test-app.apk")
            self.assertEqual(resp_qr.status_code, 200)
            qr_json = resp_qr.json()
            self.assertTrue(qr_json["success"])
            self.assertTrue(qr_json["qr_code_base64"].startswith("data:image/png;base64,"))
        finally:
            if test_out_apk.exists():
                test_out_apk.unlink()


if __name__ == "__main__":
    unittest.main()

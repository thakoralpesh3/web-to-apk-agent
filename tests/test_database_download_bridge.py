import unittest
import tempfile
import shutil
from pathlib import Path

from web2apk.template_engine import TemplateEngine
from web2apk.self_healer import SelfHealer, RUNTIME_HEALER_JS


class TestDatabaseDownloadBridge(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="web2apk_dl_test_"))

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_database_download_bridge_in_main_activity(self):
        """Verify native Base64 file saver, SQLite magic byte guardian, and download listener."""
        project_dir = self.test_dir / "dl_project"
        TemplateEngine.generate_project(
            target_dir=str(project_dir),
            app_name="DataVaultApp",
            package_name="com.datavault.app",
            version_code=1,
            version_name="1.0.0",
            is_fullscreen=False,
            remote_url="https://datavault.example.com",
            is_tv_compatible=False,
            screen_orientation="portrait"
        )

        activity_file = project_dir / "app/src/main/java/com/datavault/app/MainActivity.java"
        self.assertTrue(activity_file.exists())
        src = activity_file.read_text(encoding="utf-8")

        # 1. Native Base64 file saver & database extension guardian
        self.assertIn("saveBase64File", src)
        self.assertIn("SQLite format 3", src)
        self.assertIn(".sqlite", src)
        self.assertIn("downloadUrlWithFilename", src)

        # 2. DownloadListener handles blob with in-memory JS reader instead of ACTION_VIEW intent
        self.assertIn("url.startsWith(\"blob:\")", src)
        self.assertIn("window.AndroidApp.saveBase64File", src)
        self.assertNotIn("browserIntent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));", src)

        # 3. MediaStore & Downloads directory integration
        self.assertIn("Environment.DIRECTORY_DOWNLOADS", src)
        self.assertIn("MediaStore.Downloads", src)

        # 4. Manifest includes legacy external storage for Android 10
        manifest_file = project_dir / "app/src/main/AndroidManifest.xml"
        manifest_xml = manifest_file.read_text(encoding="utf-8")
        self.assertIn('android:requestLegacyExternalStorage="true"', manifest_xml)

    def test_client_side_download_interceptor_in_self_healer(self):
        """Verify client-side download interceptor hooks blob:, data:, and <a download>."""
        self.assertIn("Universal Database & File Download Interceptor", RUNTIME_HEALER_JS)
        self.assertIn("triggerNativeDownload", RUNTIME_HEALER_JS)
        self.assertIn("saveBase64File", RUNTIME_HEALER_JS)
        self.assertIn(".sqlite", RUNTIME_HEALER_JS)

        # Test self-healer injection into sample HTML
        sample_html = "<html><head><title>Test</title></head><body><a href='blob:test' download='db.sqlite'>Download</a></body></html>"
        html_file = self.test_dir / "index.html"
        html_file.write_text(sample_html, encoding="utf-8")

        res = SelfHealer.diagnose_and_heal_directory(self.test_dir)
        self.assertTrue(res.get("success"))
        self.assertTrue(any("Injected Runtime Healer" in r for r in res.get("repairs_made", [])))
        
        # Verify web2apk-runtime-healer.js was written with interceptor
        healer_file = self.test_dir / "web2apk-runtime-healer.js"
        self.assertTrue(healer_file.exists())
        healer_content = healer_file.read_text(encoding="utf-8")
        self.assertIn("Universal Database & File Download Interceptor", healer_content)
        self.assertIn("saveBase64File", healer_content)


if __name__ == "__main__":
    unittest.main()

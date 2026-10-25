import os
import shutil
import tempfile
import unittest
from pathlib import Path

from web2apk.template_engine import TemplateEngine, OFFLINE_HTML
from web2apk.builder import APKBuilder

class TestOfflineRetryRecovery(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_offline_html_bridge_and_fallbacks(self):
        """Verify offline.html contains native bridge calls, multi-stage fallback resolution, safety timer and reset handlers."""
        self.assertIn("AndroidApp", OFFLINE_HTML)
        self.assertIn("AndroidBridge", OFFLINE_HTML)
        self.assertIn("getLastFailedUrl", OFFLINE_HTML)
        self.assertIn("openNetworkSettings", OFFLINE_HTML)
        self.assertIn("retry-btn", OFFLINE_HTML)
        self.assertIn("refresh-btn", OFFLINE_HTML)
        self.assertIn("forceRefresh", OFFLINE_HTML)
        self.assertIn("settings-btn", OFFLINE_HTML)
        self.assertIn("addEventListener('online'", OFFLINE_HTML)
        self.assertIn("setInterval", OFFLINE_HTML)
        self.assertIn("btn.focus()", OFFLINE_HTML)
        # Ensure it does not have the old buggy fallback to '/'
        self.assertNotIn("|| '/'", OFFLINE_HTML)
        # Verify retry reset & bridge lifecycle functions
        self.assertIn("resetRetryState", OFFLINE_HTML)
        self.assertIn("window.onRetryStarting", OFFLINE_HTML)
        self.assertIn("window.onRetryFailed", OFFLINE_HTML)
        self.assertIn("retrySafetyTimer", OFFLINE_HTML)

    def test_template_engine_injects_target_url(self):
        """Verify TemplateEngine replaces __TARGET_URL__ with remote or local URL in offline.html."""
        remote_url = "https://cyber-portal.example.com/app"
        proj_dir = TemplateEngine.generate_project(
            target_dir=os.path.join(self.temp_dir, "test_proj"),
            app_name="Retry Test App",
            package_name="com.retry.testapp",
            remote_url=remote_url
        )
        
        offline_html_path = Path(proj_dir) / "app" / "src" / "main" / "assets" / "offline.html"
        self.assertTrue(offline_html_path.exists())
        content = offline_html_path.read_text(encoding="utf-8")
        self.assertNotIn("__TARGET_URL__", content)
        self.assertIn(remote_url, content)

    def test_main_activity_has_resilient_error_and_bridge_support(self):
        """Verify MainActivity.java contains WebAppInterface, lastFailedUrl, NetworkCallback, TV keys and pull-to-refresh."""
        proj_dir = TemplateEngine.generate_project(
            target_dir=os.path.join(self.temp_dir, "test_proj_java"),
            app_name="Retry Java App",
            package_name="com.retry.javaapp",
            remote_url="https://mysite.com"
        )
        
        main_activity_path = Path(proj_dir) / "app" / "src" / "main" / "java" / "com" / "retry" / "javaapp" / "MainActivity.java"
        self.assertTrue(main_activity_path.exists())
        java_code = main_activity_path.read_text(encoding="utf-8")

        # Native bridge & WebAppInterface
        self.assertIn("public class WebAppInterface", java_code)
        self.assertIn("@JavascriptInterface", java_code)
        self.assertIn("webView.addJavascriptInterface(appInterface, \"AndroidApp\");", java_code)
        self.assertIn("webView.addJavascriptInterface(appInterface, \"AndroidBridge\");", java_code)
        self.assertIn("public void retry()", java_code)
        self.assertIn("public void reload()", java_code)
        self.assertIn("public String getLastFailedUrl()", java_code)
        self.assertIn("public void openNetworkSettings()", java_code)

        # lastFailedUrl & showOfflinePage DOM bridge
        self.assertIn("private String lastFailedUrl", java_code)
        self.assertIn("private boolean isShowingOffline", java_code)
        self.assertIn("public void retryConnection()", java_code)
        self.assertIn("public void refreshPage()", java_code)
        self.assertIn("private void showOfflinePage(String failingUrl)", java_code)
        self.assertIn("onRetryStarting()", java_code)
        self.assertIn("onRetryFailed()", java_code)

        # Subresource error filtering in WebViewClient
        self.assertIn("request.isForMainFrame()", java_code)
        self.assertIn(".endsWith(\".png\")", java_code)
        self.assertIn(".endsWith(\".css\")", java_code)
        self.assertIn(".endsWith(\".js\")", java_code)

        # NetworkCallback on API 21+
        self.assertIn("ConnectivityManager.NetworkCallback", java_code)
        self.assertIn("NetworkRequest.Builder()", java_code)
        self.assertIn("registerNetworkCallback()", java_code)
        self.assertIn("unregisterNetworkCallback()", java_code)

        # Ergonomic Pull-to-refresh
        self.assertIn("setOnTouchListener", java_code)
        self.assertIn("isPullRefreshing", java_code)
        self.assertIn("pullThreshold", java_code)
        self.assertIn("density", java_code)
        self.assertNotIn("androidx.swiperefreshlayout", java_code)

        # TV Remote Keys & Dedicated Refresh keys
        self.assertIn("KEYCODE_MENU", java_code)
        self.assertIn("KEYCODE_MEDIA_PLAY_PAUSE", java_code)
        self.assertIn("KEYCODE_REFRESH", java_code)
        self.assertIn("KEYCODE_F5", java_code)
        self.assertIn("KEYCODE_DPAD_CENTER", java_code)

    def test_compilation_and_apk_build_succeeds(self):
        """Compile a real APK using the new MainActivity to guarantee javac/R8 compatibility with android.jar."""
        web_dir = Path(self.temp_dir) / "web_sample"
        web_dir.mkdir(parents=True, exist_ok=True)
        (web_dir / "index.html").write_text("<!DOCTYPE html><html><body><h1>Offline Test</h1></body></html>")

        builder = APKBuilder()
        res = builder.build_from_directory(
            source_dir=str(web_dir),
            app_name="Offline Test Suite",
            package_name="com.test.offlinesuite",
            version_name="1.0.0",
            version_code=1,
            is_tv_compatible=True,
            is_fullscreen=False,
            screen_orientation="sensor"
        )
        self.assertTrue(res.get("success"), f"Build failed: {res.get('error')}")
        apk_path = res.get("apk_path")
        self.assertIsNotNone(apk_path)
        self.assertTrue(Path(apk_path).exists())

    def test_offline_agent_execution_and_cache_mode(self):
        """Verify GeminiAdvisor handles offline gracefully and template uses LOAD_CACHE_ELSE_NETWORK."""
        from web2apk.ai_advisor import GeminiAdvisor
        from unittest.mock import patch

        # 1. Probe works
        self.assertIsInstance(GeminiAdvisor.is_online(), bool)

        # 2. Simulated offline
        with patch.object(GeminiAdvisor, "is_online", return_value=False):
            self.assertFalse(GeminiAdvisor.is_available())
            models = GeminiAdvisor.discover_available_models()
            self.assertTrue(len(models) > 0)

            # Heuristic offline analysis
            opt = GeminiAdvisor.analyze_and_optimize_code("<h1>Test</h1>", "TestApp")
            self.assertTrue(opt.get("success"))
            self.assertEqual(opt.get("model"), "offline-engine")

            # Heuristic offline responsive CSS
            css_res = GeminiAdvisor.restyle_responsive("<h1>Test</h1>", "TestApp")
            self.assertTrue(css_res.get("success"))
            self.assertEqual(css_res.get("model"), "offline-engine")

            # Heuristic offline store metadata
            meta = GeminiAdvisor.generate_play_store_metadata("TestApp")
            self.assertTrue(meta.get("success"))
            self.assertEqual(meta.get("model"), "offline-engine")

        # 3. Verify template contains LOAD_CACHE_ELSE_NETWORK
        proj_dir = TemplateEngine.generate_project(
            target_dir=os.path.join(self.temp_dir, "test_proj_offline"),
            app_name="Offline Cache App",
            package_name="com.offline.cacheapp",
            remote_url="https://offline-example.com"
        )
        main_activity_path = Path(proj_dir) / "app" / "src" / "main" / "java" / "com" / "offline" / "cacheapp" / "MainActivity.java"
        java_code = main_activity_path.read_text(encoding="utf-8")
        self.assertIn("webSettings.setCacheMode(WebSettings.LOAD_CACHE_ELSE_NETWORK);", java_code)
        self.assertIn("TARGET_URL.startsWith(\"file:///android_asset/\")", java_code)

if __name__ == "__main__":
    unittest.main()

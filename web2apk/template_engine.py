import os
import re
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List

OFFLINE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>Connection Error</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background: radial-gradient(circle at center, #1e293b 0%, #090d16 100%);
            color: #ffffff;
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 24px;
            text-align: center;
            user-select: none;
            -webkit-user-select: none;
        }
        .card {
            background: rgba(15, 23, 42, 0.9);
            border: 1px solid rgba(56, 189, 248, 0.35);
            box-shadow: 0 0 40px rgba(56, 189, 248, 0.25);
            padding: 44px 32px;
            border-radius: 24px;
            max-width: 460px;
            width: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
        }
        .icon {
            width: 80px;
            height: 80px;
            background: rgba(56, 189, 248, 0.12);
            border: 2px solid #38bdf8;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 24px;
            color: #38bdf8;
            animation: pulse 2.5s infinite;
        }
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(56, 189, 248, 0.4); }
            70% { box-shadow: 0 0 0 16px rgba(56, 189, 248, 0); }
            100% { box-shadow: 0 0 0 0 rgba(56, 189, 248, 0); }
        }
        h2 { font-size: 1.6rem; margin-bottom: 10px; font-weight: 700; letter-spacing: -0.5px; }
        p { color: #94a3b8; font-size: 0.95rem; margin-bottom: 24px; line-height: 1.6; }
        .url-preview {
            display: inline-block;
            font-family: monospace;
            font-size: 0.8rem;
            color: #38bdf8;
            background: rgba(56, 189, 248, 0.08);
            border: 1px solid rgba(56, 189, 248, 0.2);
            border-radius: 8px;
            padding: 6px 12px;
            margin-bottom: 24px;
            max-width: 100%;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .btn-group {
            display: flex;
            flex-direction: column;
            gap: 12px;
            width: 100%;
        }
        button {
            border: 0;
            padding: 14px 28px;
            border-radius: 14px;
            font-size: 1rem;
            font-weight: 700;
            cursor: pointer;
            width: 100%;
            transition: all 0.2s ease;
            outline: none;
        }
        .btn-primary {
            background: linear-gradient(135deg, #38bdf8 0%, #6366f1 100%);
            color: #ffffff;
            box-shadow: 0 0 20px rgba(56, 189, 248, 0.4);
        }
        .btn-secondary {
            background: rgba(255, 255, 255, 0.08);
            color: #cbd5e1;
            border: 1px solid rgba(255, 255, 255, 0.15);
        }
        button:hover, button:focus {
            transform: scale(1.02);
            box-shadow: 0 0 25px rgba(56, 189, 248, 0.6);
            outline: 2px solid #38bdf8;
        }
        .status {
            font-size: 0.85rem;
            color: #64748b;
            margin-top: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        .spinner {
            display: none;
            width: 16px;
            height: 16px;
            border: 2px solid rgba(56, 189, 248, 0.3);
            border-top-color: #38bdf8;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">
            <svg width="40" height="40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 5.636a9 9 0 010 12.728m0 0l-2.829-2.829m2.829 2.829L21 21M15.536 8.464a5 5 0 010 7.072m0 0l-2.829-2.829m-4.243 4.243a9 9 0 01-6.364-2.636M3 3l18 18M9.879 9.879a3 3 0 004.242 4.242M6.343 6.343A9 9 0 003 12c0 2.485 1.007 4.735 2.636 6.364" />
            </svg>
        </div>
        <h2>Connection Lost</h2>
        <p>Unable to load the application. Please check your internet connection or Wi-Fi settings and tap retry.</p>
        <div class="url-preview" id="url-display" style="display: none;"></div>
        <div class="btn-group">
            <button id="retry-btn" class="btn-primary" onclick="retry()">⚡ Retry Connection</button>
            <button id="refresh-btn" class="btn-secondary" onclick="forceRefresh()">🔄 Refresh Page</button>
            <button id="settings-btn" class="btn-secondary" onclick="openSettings()">⚙️ Network Settings</button>
        </div>
        <div class="status">
            <span class="spinner" id="spinner"></span>
            <span id="status-txt">Tap Retry to reconnect</span>
        </div>
    </div>
    <script>
        const DEFAULT_URL = "__TARGET_URL__";
        let isRetrying = false;
        let retrySafetyTimer = null;

        function resetRetryState(msg) {
            isRetrying = false;
            if (retrySafetyTimer) {
                clearTimeout(retrySafetyTimer);
                retrySafetyTimer = null;
            }
            const statusTxt = document.getElementById('status-txt');
            const spinner = document.getElementById('spinner');
            const btn = document.getElementById('retry-btn');
            if (statusTxt) statusTxt.innerText = msg || 'Tap Retry to reconnect';
            if (spinner) spinner.style.display = 'none';
            if (btn) {
                btn.disabled = false;
                btn.innerText = 'Retry Connection';
                btn.focus();
            }
        }

        window.onRetryStarting = function() {
            isRetrying = true;
            const statusTxt = document.getElementById('status-txt');
            const spinner = document.getElementById('spinner');
            const btn = document.getElementById('retry-btn');
            if (statusTxt) statusTxt.innerText = 'Reconnecting...';
            if (spinner) spinner.style.display = 'inline-block';
            if (btn) {
                btn.disabled = true;
                btn.innerText = 'Connecting...';
            }
        };

        window.onRetryFailed = function(msg) {
            resetRetryState(msg || 'Still offline. Please check network and retry.');
        };

        function getTargetUrl() {
            try {
                if (window.AndroidApp && typeof window.AndroidApp.getLastFailedUrl === 'function') {
                    const bridgeUrl = window.AndroidApp.getLastFailedUrl();
                    if (bridgeUrl && bridgeUrl.length > 0 && bridgeUrl !== 'about:blank' && !bridgeUrl.includes('offline.html')) return bridgeUrl;
                }
            } catch(e) {}
            try {
                const searchParams = new URLSearchParams(window.location.search);
                const queryUrl = searchParams.get('target_url');
                if (queryUrl && queryUrl !== '/' && queryUrl !== 'null' && !queryUrl.includes('offline.html')) return queryUrl;
            } catch(e) {}
            try {
                if (window.location.hash && window.location.hash.length > 1) {
                    const hashUrl = decodeURIComponent(window.location.hash.substring(1));
                    if (hashUrl && hashUrl !== '/' && (hashUrl.startsWith('http') || hashUrl.startsWith('file:///android_asset/')) && !hashUrl.includes('offline.html')) return hashUrl;
                }
            } catch(e) {}
            try {
                const storedUrl = localStorage.getItem('last_visited_url');
                if (storedUrl && storedUrl !== '/' && (storedUrl.startsWith('http') || storedUrl.startsWith('file:///android_asset/')) && !storedUrl.includes('offline.html')) {
                    return storedUrl;
                }
            } catch(e) {}
            return (DEFAULT_URL && !DEFAULT_URL.startsWith('__')) ? DEFAULT_URL : 'file:///android_asset/index.html';
        }

        const initialTarget = getTargetUrl();
        try {
            if (initialTarget && initialTarget.startsWith('http')) {
                const urlDisp = document.getElementById('url-display');
                if (urlDisp) {
                    urlDisp.innerText = initialTarget;
                    urlDisp.style.display = 'inline-block';
                }
            }
        } catch(e) {}

        function retry() {
            if (isRetrying) return;
            window.onRetryStarting();

            if (retrySafetyTimer) clearTimeout(retrySafetyTimer);
            retrySafetyTimer = setTimeout(() => {
                resetRetryState('Connection timed out. Tap Retry to try again.');
            }, 4000);

            try {
                if (window.AndroidApp && typeof window.AndroidApp.retry === 'function') {
                    window.AndroidApp.retry();
                    return;
                }
                if (window.AndroidBridge && typeof window.AndroidBridge.retry === 'function') {
                    window.AndroidBridge.retry();
                    return;
                }
            } catch(e) {}

            setTimeout(() => {
                const dest = getTargetUrl();
                if (dest && dest !== '/' && dest !== 'null') {
                    window.location.replace(dest);
                } else {
                    window.location.reload();
                }
            }, 500);
        }

        function forceRefresh() {
            window.onRetryStarting();
            if (retrySafetyTimer) clearTimeout(retrySafetyTimer);
            retrySafetyTimer = setTimeout(() => {
                resetRetryState('Refresh timed out. Tap Retry to try again.');
            }, 4000);

            try {
                if (window.AndroidApp && typeof window.AndroidApp.reload === 'function') {
                    window.AndroidApp.reload();
                    return;
                }
                if (window.AndroidBridge && typeof window.AndroidBridge.reload === 'function') {
                    window.AndroidBridge.reload();
                    return;
                }
            } catch(e) {}

            try {
                const dest = getTargetUrl();
                if (dest && dest !== '/' && dest !== 'null') {
                    window.location.replace(dest);
                } else {
                    window.location.reload();
                }
            } catch(e) {}
        }

        function openSettings() {
            try {
                if (window.AndroidApp && typeof window.AndroidApp.openNetworkSettings === 'function') {
                    window.AndroidApp.openNetworkSettings();
                    return;
                }
                if (window.AndroidBridge && typeof window.AndroidBridge.openNetworkSettings === 'function') {
                    window.AndroidBridge.openNetworkSettings();
                    return;
                }
            } catch(e) {}
        }

        window.addEventListener('online', () => {
            const statusTxt = document.getElementById('status-txt');
            if (statusTxt) statusTxt.innerText = 'Network detected! Reconnecting...';
            setTimeout(retry, 400);
        });

        setInterval(() => {
            if (navigator.onLine && !isRetrying) {
                retry();
            }
        }, 8000);

        document.addEventListener('DOMContentLoaded', () => {
            const btn = document.getElementById('retry-btn');
            if (btn) btn.focus();
        });
    </script>
</body>
</html>"""

class TemplateEngine:
    """
    Generates complete native Android Studio / Gradle project templates
    configured for Smartphone, Tablet, and Android TV / Google TV.
    """

    @staticmethod
    def generate_project(
        target_dir: str,
        app_name: str,
        package_name: str,
        version_name: str = "1.0.0",
        version_code: int = 1,
        is_tv_compatible: bool = True,
        is_fullscreen: bool = False,
        screen_orientation: str = "sensor",
        remote_url: Optional[str] = None,
        extra_permissions: Optional[List[str]] = None,
        theme_color: str = "#0f172a"
    ) -> str:
        project_path = Path(target_dir)
        if project_path.exists():
            shutil.rmtree(project_path)
        project_path.mkdir(parents=True, exist_ok=True)

        app_path = project_path / "app"
        src_main = app_path / "src" / "main"
        assets_dir = src_main / "assets"
        res_dir = src_main / "res"
        
        package_rel_path = package_name.replace(".", "/")
        java_dir = src_main / "java" / package_rel_path
        java_dir.mkdir(parents=True, exist_ok=True)
        assets_dir.mkdir(parents=True, exist_ok=True)
        res_dir.mkdir(parents=True, exist_ok=True)
        target_initial_url = remote_url if remote_url else "file:///android_asset/index.html"
        offline_content = OFFLINE_HTML.replace("__TARGET_URL__", target_initial_url)
        (assets_dir / "offline.html").write_text(offline_content, encoding="utf-8")

        manifest_content = TemplateEngine._get_manifest(
            package_name=package_name,
            app_name=app_name,
            is_tv=is_tv_compatible,
            orientation=screen_orientation,
            extra_permissions=extra_permissions or []
        )
        (src_main / "AndroidManifest.xml").write_text(manifest_content, encoding="utf-8")

        main_activity_content = TemplateEngine._get_main_activity(
            package_name=package_name,
            is_fullscreen=is_fullscreen,
            remote_url=remote_url,
            is_tv=is_tv_compatible,
            theme_color=theme_color
        )
        (java_dir / "MainActivity.java").write_text(main_activity_content, encoding="utf-8")

        TemplateEngine._generate_res_files(res_dir, app_name)

        TemplateEngine._generate_gradle_files(
            project_path=project_path,
            app_path=app_path,
            package_name=package_name,
            version_code=version_code,
            version_name=version_name
        )

        return str(project_path)

    @staticmethod
    def _get_manifest(
        package_name: str,
        app_name: str,
        is_tv: bool,
        orientation: str,
        extra_permissions: List[str]
    ) -> str:
        tv_features = ""
        tv_intent_filters = """
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>"""
        banner_attr = ""

        if is_tv:
            tv_features = """
    <!-- Android TV & Leanback Compatibility -->
    <uses-feature android:name="android.software.leanback" android:required="false" />
    <uses-feature android:name="android.hardware.touchscreen" android:required="false" />
    <uses-feature android:name="android.hardware.gamepad" android:required="false" />
    <uses-feature android:name="android.hardware.faketouch" android:required="false" />
    <uses-feature android:name="android.hardware.telephony" android:required="false" />
    <uses-feature android:name="android.hardware.camera" android:required="false" />
    <uses-feature android:name="android.hardware.camera.autofocus" android:required="false" />
    <uses-feature android:name="android.hardware.bluetooth" android:required="false" />
    <uses-feature android:name="android.hardware.nfc" android:required="false" />
    <uses-feature android:name="android.hardware.location" android:required="false" />
    <uses-feature android:name="android.hardware.location.gps" android:required="false" />
    <uses-feature android:name="android.hardware.location.network" android:required="false" />
    <uses-feature android:name="android.hardware.microphone" android:required="false" />
    <uses-feature android:name="android.hardware.wifi" android:required="false" />
            """
            banner_attr = 'android:banner="@drawable/tv_banner"'
            tv_intent_filters = """
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LEANBACK_LAUNCHER" />
            </intent-filter>
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>"""

        effective_orientation = "landscape" if is_tv and orientation in ["sensor", "portrait", "portrait_reverse", ""] else orientation
        screen_orientation_attr = f'android:screenOrientation="{effective_orientation}"' if effective_orientation != "sensor" else ""

        base_permissions = [
            "android.permission.INTERNET",
            "android.permission.ACCESS_NETWORK_STATE",
            "android.permission.ACCESS_WIFI_STATE",
            "android.permission.MODIFY_AUDIO_SETTINGS",
            "android.permission.READ_EXTERNAL_STORAGE",
            "android.permission.WRITE_EXTERNAL_STORAGE",
            "android.permission.ACCESS_FINE_LOCATION",
            "android.permission.ACCESS_COARSE_LOCATION"
        ]
        all_perms = list(dict.fromkeys(base_permissions + extra_permissions))
        perm_tags = "\n".join([f'    <uses-permission android:name="{p}" />' for p in all_perms])

        return f"""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{package_name}">

    <!-- SDK Compatibility -->
    <uses-sdk android:minSdkVersion="21" android:targetSdkVersion="34" />

    <!-- Permissions -->
{perm_tags}
{tv_features}

    <application
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:roundIcon="@mipmap/ic_launcher_round"
        android:label="@string/app_name"
        android:supportsRtl="true"
        android:theme="@style/Theme.Web2APK.Fullscreen"
        android:hardwareAccelerated="true"
        android:usesCleartextTraffic="true"
        android:requestLegacyExternalStorage="true"
        android:enableOnBackInvokedCallback="true"
        {banner_attr}>

        <activity
            android:name=".MainActivity"
            android:exported="true"
            {screen_orientation_attr}
            {banner_attr}
            android:supportsPictureInPicture="true"
            android:configChanges="orientation|keyboardHidden|screenSize|screenLayout|smallestScreenSize|uiMode"
            android:windowSoftInputMode="adjustResize">
            
            {tv_intent_filters}
        </activity>

    </application>

</manifest>
"""

    @staticmethod
    def _get_main_activity(
        package_name: str,
        is_fullscreen: bool,
        remote_url: Optional[str],
        is_tv: bool,
        theme_color: str
    ) -> str:
        fullscreen_code = ""
        if is_fullscreen:
            fullscreen_code = """
        getWindow().getDecorView().setSystemUiVisibility(
            View.SYSTEM_UI_FLAG_LAYOUT_STABLE
            | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
            | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
            | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
            | View.SYSTEM_UI_FLAG_FULLSCREEN
            | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
        );
            """

        clean_theme = theme_color if re.match(r"^#[0-9a-fA-F]{6}$", theme_color) else "#0f172a"
        target_initial_url = remote_url if remote_url else "file:///android_asset/index.html"

        return f"""package {package_name};

import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.DownloadManager;
import android.app.UiModeManager;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ActivityInfo;
import android.content.pm.PackageManager;
import android.content.res.Configuration;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.NetworkRequest;
import android.net.NetworkInfo;
import android.net.Uri;
import android.net.http.SslError;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.os.Message;
import android.os.SystemClock;
import android.provider.Settings;
import android.view.InputDevice;
import android.view.KeyEvent;
import android.view.MotionEvent;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.ConsoleMessage;
import android.webkit.CookieManager;
import android.webkit.DownloadListener;
import android.webkit.GeolocationPermissions;
import android.webkit.JavascriptInterface;
import android.webkit.PermissionRequest;
import android.webkit.SslErrorHandler;
import android.webkit.URLUtil;
import android.webkit.ValueCallback;
import android.webkit.WebBackForwardList;
import android.webkit.WebChromeClient;
import android.webkit.WebHistoryItem;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.ProgressBar;
import android.widget.Toast;
import android.window.OnBackInvokedCallback;
import android.window.OnBackInvokedDispatcher;
import android.util.Base64;
import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStream;
import android.media.MediaScannerConnection;
import android.content.ContentValues;
import android.provider.MediaStore;

public class MainActivity extends Activity {{

    private WebView webView;
    private ProgressBar progressBar;
    private FrameLayout customViewContainer;
    private View customView;
    private WebChromeClient.CustomViewCallback customViewCallback;
    private int originalOrientation;
    private int originalSystemUiVisibility;
    private WebChromeClient webChromeClient;
    private ValueCallback<Uri[]> uploadMessage;
    private final static int FILECHOOSER_RESULTCODE = 1;
    private final static int PERMISSIONS_REQUEST_LOCATION = 1002;
    private String pendingGeoOrigin = null;
    private GeolocationPermissions.Callback pendingGeoCallback = null;
    private final String TARGET_URL = "{target_initial_url}";
    private String lastFailedUrl = "{target_initial_url}";
    private boolean isShowingOffline = false;
    private ConnectivityManager.NetworkCallback networkCallback;
    private float touchDownY = 0f;
    private float touchDownX = 0f;
    private boolean isPullRefreshing = false;

    // Android TV Virtual Mouse Pointer Engine
    private FrameLayout tvMouseContainer;
    private View tvMouseClickRing;
    private ImageView tvMouseCursor;
    private float cursorX = 0f;
    private float cursorY = 0f;
    private boolean isMouseMode = false;
    private final float BASE_CURSOR_SPEED = 20f;
    private final float MAX_CURSOR_SPEED = 60f;
    private Handler mouseHandler = new Handler(Looper.getMainLooper());
    private boolean isTvDevice = false;
    private boolean cursorPositionInitialized = false;
    private WebAppInterface appInterface;
    private long lastBackPressTime = 0;
    private static final long BACK_PRESS_INTERVAL = 2000;
    private long lastBackInvocationTime = 0;

    public class WebAppInterface {{
        private volatile boolean isLightsOutActive = false;

        @JavascriptInterface
        public void setLightsOutActive(boolean active) {{
            isLightsOutActive = active;
        }}

        @JavascriptInterface
        public boolean isLightsOutActive() {{
            return isLightsOutActive;
        }}

        @JavascriptInterface
        public void showToast(String message, boolean isLong) {{
            runOnUiThread(new Runnable() {{
                @Override
                public void run() {{
                    Toast.makeText(MainActivity.this, message, isLong ? Toast.LENGTH_LONG : Toast.LENGTH_SHORT).show();
                }}
            }});
        }}

        @JavascriptInterface
        public void exitApp() {{
            runOnUiThread(new Runnable() {{
                @Override
                public void run() {{
                    finish();
                }}
            }});
        }}

        @JavascriptInterface
        public void vibrate(long duration) {{
            try {{
                android.os.Vibrator v = (android.os.Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
                if (v != null) {{
                    v.vibrate(Math.min(duration, 1000));
                }}
            }} catch (Exception ignored) {{}}
        }}

        @JavascriptInterface
        public void retry() {{
            runOnUiThread(new Runnable() {{
                @Override
                public void run() {{
                    retryConnection();
                }}
            }});
        }}

        @JavascriptInterface
        public void reload() {{
            runOnUiThread(new Runnable() {{
                @Override
                public void run() {{
                    refreshPage();
                }}
            }});
        }}

        @JavascriptInterface
        public String getLastFailedUrl() {{
            return (lastFailedUrl != null && !lastFailedUrl.isEmpty() && !lastFailedUrl.startsWith("file:///android_asset/offline.html"))
                ? lastFailedUrl : TARGET_URL;
        }}

        @JavascriptInterface
        public boolean isOnline() {{
            return isNetworkAvailable();
        }}

        @JavascriptInterface
        public void openNetworkSettings() {{
            try {{
                Intent intent = new Intent(Settings.ACTION_WIFI_SETTINGS);
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                startActivity(intent);
            }} catch (Exception e) {{
                try {{
                    Intent intent = new Intent(Settings.ACTION_SETTINGS);
                    intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                    startActivity(intent);
                }} catch (Exception ignored) {{}}
            }}
        }}

        @JavascriptInterface
        public void saveBase64File(final String base64Data, final String suggestedFilename, final String mimeType) {{
            if (base64Data == null || base64Data.isEmpty()) return;
            new Thread(new Runnable() {{
                @Override
                public void run() {{
                    try {{
                        String rawData = base64Data;
                        String detectedMime = mimeType != null ? mimeType : "";
                        if (rawData.startsWith("data:")) {{
                            int commaIdx = rawData.indexOf(",");
                            if (commaIdx != -1) {{
                                String header = rawData.substring(5, commaIdx);
                                if (header.contains(";")) {{
                                    String[] parts = header.split(";");
                                    if (detectedMime.isEmpty() && parts.length > 0) {{
                                        detectedMime = parts[0];
                                    }}
                                }}
                                rawData = rawData.substring(commaIdx + 1);
                            }}
                        }}
                        rawData = rawData.replaceAll("\\s+", "");
                        byte[] fileBytes = Base64.decode(rawData, Base64.DEFAULT);
                        if (fileBytes == null || fileBytes.length == 0) return;

                        String safeName = (suggestedFilename != null && !suggestedFilename.trim().isEmpty())
                                ? suggestedFilename.trim() : "database_export";

                        boolean isSqlite = false;
                        if (fileBytes.length >= 16) {{
                            String header16 = new String(fileBytes, 0, Math.min(16, fileBytes.length), java.nio.charset.StandardCharsets.US_ASCII);
                            if (header16.startsWith("SQLite format 3")) {{
                                isSqlite = true;
                            }}
                        }}

                        boolean isZip = (fileBytes.length >= 4 && fileBytes[0] == 0x50 && fileBytes[1] == 0x4B && fileBytes[2] == 0x03 && fileBytes[3] == 0x04);
                        boolean isGzip = (fileBytes.length >= 2 && (fileBytes[0] & 0xFF) == 0x1F && (fileBytes[1] & 0xFF) == 0x8B);

                        String lowerName = safeName.toLowerCase();
                        if (isSqlite && !lowerName.endsWith(".sqlite") && !lowerName.endsWith(".db") && !lowerName.endsWith(".sqlite3")) {{
                            safeName = safeName.replaceAll("\\.[^.]+$", "") + ".sqlite";
                        }} else if (isZip && !lowerName.endsWith(".zip")) {{
                            safeName = safeName.replaceAll("\\.[^.]+$", "") + ".zip";
                        }} else if (isGzip && !lowerName.endsWith(".gz") && !lowerName.endsWith(".tar.gz")) {{
                            safeName = safeName.replaceAll("\\.[^.]+$", "") + ".gz";
                        }} else if (lowerName.endsWith(".html") || lowerName.endsWith(".htm") || !lowerName.contains(".")) {{
                            try {{
                                String snippet = new String(fileBytes, 0, Math.min(256, fileBytes.length), java.nio.charset.StandardCharsets.UTF_8).trim();
                                if (snippet.startsWith("{{\") || snippet.startsWith("[")) {{
                                    safeName = safeName.replaceAll("\\.[^.]+$", "") + ".json";
                                }} else if (snippet.toUpperCase().startsWith("CREATE ") || snippet.toUpperCase().startsWith("INSERT ") ||
                                           snippet.toUpperCase().startsWith("BEGIN ") || snippet.startsWith("--") || snippet.startsWith("/*")) {{
                                    safeName = safeName.replaceAll("\\.[^.]+$", "") + ".sql";
                                }} else if (detectedMime.contains("csv") || snippet.contains(",")) {{
                                    safeName = safeName.replaceAll("\\.[^.]+$", "") + ".csv";
                                }} else if (isSqlite) {{
                                    safeName = safeName.replaceAll("\\.[^.]+$", "") + ".sqlite";
                                }}
                            }} catch (Exception ignored) {{}}
                        }}

                        final String finalFilename = safeName;
                        boolean saved = false;

                        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {{
                            try {{
                                ContentValues values = new ContentValues();
                                values.put(MediaStore.Downloads.DISPLAY_NAME, finalFilename);
                                values.put(MediaStore.Downloads.MIME_TYPE, !detectedMime.isEmpty() ? detectedMime : "application/octet-stream");
                                values.put(MediaStore.Downloads.IS_PENDING, 1);
                                Uri uri = getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values);
                                if (uri != null) {{
                                    OutputStream os = getContentResolver().openOutputStream(uri);
                                    if (os != null) {{
                                        os.write(fileBytes);
                                        os.flush();
                                        os.close();
                                    }}
                                    values.clear();
                                    values.put(MediaStore.Downloads.IS_PENDING, 0);
                                    getContentResolver().update(uri, values, null, null);
                                    saved = true;
                                }}
                            }} catch (Exception e) {{
                                saved = false;
                            }}
                        }}

                        if (!saved) {{
                            File downloadsDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS);
                            if (downloadsDir != null) {{
                                if (!downloadsDir.exists()) downloadsDir.mkdirs();
                                File targetFile = new File(downloadsDir, finalFilename);
                                FileOutputStream fos = new FileOutputStream(targetFile);
                                fos.write(fileBytes);
                                fos.flush();
                                fos.close();
                                MediaScannerConnection.scanFile(MainActivity.this, new String[]{{targetFile.getAbsolutePath()}}, null, null);
                                saved = true;
                            }}
                        }}

                        if (saved) {{
                            runOnUiThread(new Runnable() {{
                                @Override
                                public void run() {{
                                    Toast.makeText(MainActivity.this, "Database saved to Downloads: " + finalFilename, Toast.LENGTH_LONG).show();
                                }}
                            }});
                        }}
                    }} catch (final Exception err) {{
                        runOnUiThread(new Runnable() {{
                            @Override
                            public void run() {{
                                Toast.makeText(MainActivity.this, "Download error: " + err.getMessage(), Toast.LENGTH_SHORT).show();
                            }}
                        }});
                    }}
                }}
            }}).start();
        }}

        @JavascriptInterface
        public void downloadUrlWithFilename(final String url, final String filename, final String mimeType) {{
            if (url == null || url.isEmpty()) return;
            if (url.startsWith("blob:")) {{
                runOnUiThread(new Runnable() {{
                    @Override
                    public void run() {{
                        String js = "(function() {{" +
                            "  try {{" +
                            "    var u = '" + url + "';" +
                            "    var cached = (window.__blob_cache && window.__blob_cache[u]) ? window.__blob_cache[u] : null;" +
                            "    function send(blobObj) {{" +
                            "      var reader = new FileReader();" +
                            "      reader.onloadend = function() {{" +
                            "        if (window.AndroidApp && typeof window.AndroidApp.saveBase64File === 'function') {{" +
                            "          window.AndroidApp.saveBase64File(reader.result, '" + (filename != null && !filename.isEmpty() ? filename : "database_export.sqlite") + "', blobObj.type || '" + (mimeType != null ? mimeType : "") + "');" +
                            "        }}" +
                            "      }};" +
                            "      reader.readAsDataURL(blobObj);" +
                            "    }}" +
                            "    if (cached) {{" +
                            "      send(cached);" +
                            "    }} else {{" +
                            "      fetch(u).then(function(r){{ return r.blob(); }}).then(send).catch(function(e){{ console.error(e); }});" +
                            "    }}" +
                            "  }} catch(e) {{ console.error(e); }}" +
                            "}})();";
                        if (webView != null) webView.evaluateJavascript(js, null);
                    }}
                }});
                return;
            }}
            if (url.startsWith("data:")) {{
                saveBase64File(url, filename, mimeType);
                return;
            }}

            new Thread(new Runnable() {{
                @Override
                public void run() {{
                    java.net.HttpURLConnection conn = null;
                    try {{
                        java.net.URL u = new java.net.URL(url);
                        conn = (java.net.HttpURLConnection) u.openConnection();
                        conn.setRequestMethod("GET");
                        conn.setConnectTimeout(15000);
                        conn.setReadTimeout(30000);
                        conn.setInstanceFollowRedirects(true);
                        String cookies = CookieManager.getInstance().getCookie(url);
                        if (cookies != null) conn.setRequestProperty("Cookie", cookies);
                        String ua = (webView != null && webView.getSettings() != null) ? webView.getSettings().getUserAgentString() : null;
                        if (ua != null) conn.setRequestProperty("User-Agent", ua);
                        conn.connect();

                        int code = conn.getResponseCode();
                        if (code >= 200 && code < 300) {{
                            String disp = conn.getHeaderField("Content-Disposition");
                            String cType = conn.getContentType();
                            String resolvedName = filename;
                            if ((resolvedName == null || resolvedName.isEmpty()) && disp != null) {{
                                java.util.regex.Matcher m = java.util.regex.Pattern.compile("filename\\*?=['\"]?(?:UTF-8'')?([^;'\"]+)['\"]?", java.util.regex.Pattern.CASE_INSENSITIVE).matcher(disp);
                                if (m.find()) resolvedName = m.group(1).trim();
                            }}
                            if (resolvedName == null || resolvedName.isEmpty()) {{
                                resolvedName = URLUtil.guessFileName(url, disp, cType);
                            }}

                            java.io.InputStream in = conn.getInputStream();
                            java.io.ByteArrayOutputStream baos = new java.io.ByteArrayOutputStream();
                            byte[] buffer = new byte[8192];
                            int read;
                            while ((read = in.read(buffer)) != -1) {{
                                baos.write(buffer, 0, read);
                            }}
                            in.close();
                            byte[] data = baos.toByteArray();
                            if (data.length > 0) {{
                                String b64 = Base64.encodeToString(data, Base64.NO_WRAP);
                                saveBase64File(b64, resolvedName, cType);
                                return;
                            }}
                        }}
                    }} catch (Exception ignored) {{
                    }} finally {{
                        if (conn != null) conn.disconnect();
                    }}

                    // Fallback to DownloadManager
                    runOnUiThread(new Runnable() {{
                        @Override
                        public void run() {{
                            try {{
                                DownloadManager.Request request = new DownloadManager.Request(Uri.parse(url));
                                String targetName = (filename != null && !filename.trim().isEmpty()) ? filename.trim() : URLUtil.guessFileName(url, null, mimeType);
                                if (mimeType != null && !mimeType.isEmpty()) request.setMimeType(mimeType);
                                String cookies = CookieManager.getInstance().getCookie(url);
                                if (cookies != null) request.addRequestHeader("cookie", cookies);
                                request.setTitle(targetName);
                                request.setDescription("Downloading " + targetName);
                                request.allowScanningByMediaScanner();
                                request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
                                request.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, targetName);
                                DownloadManager dm = (DownloadManager) getSystemService(DOWNLOAD_SERVICE);
                                if (dm != null) {{
                                    dm.enqueue(request);
                                    Toast.makeText(MainActivity.this, "Downloading: " + targetName, Toast.LENGTH_SHORT).show();
                                }}
                            }} catch (Exception e) {{
                                Toast.makeText(MainActivity.this, "Download failed: " + e.getMessage(), Toast.LENGTH_SHORT).show();
                            }}
                        }}
                    }});
                }}
            }}).start();
        }}
    }}

    public void retryConnection() {{
        runOnUiThread(new Runnable() {{
            @Override
            public void run() {{
                if (webView == null) return;
                isShowingOffline = false;
                String urlToLoad = (lastFailedUrl != null && !lastFailedUrl.isEmpty() && !lastFailedUrl.contains("offline.html") && !lastFailedUrl.equals("about:blank"))
                    ? lastFailedUrl : TARGET_URL;
                if (progressBar != null) progressBar.setVisibility(View.VISIBLE);
                try {{
                    if (webView.getUrl() != null && webView.getUrl().contains("offline.html")) {{
                        webView.evaluateJavascript("if (typeof window.onRetryStarting === 'function') window.onRetryStarting();", null);
                    }}
                    webView.stopLoading();
                    webView.getSettings().setCacheMode(isNetworkAvailable() ? WebSettings.LOAD_DEFAULT : WebSettings.LOAD_CACHE_ELSE_NETWORK);
                    webView.loadUrl(urlToLoad);
                    webView.postDelayed(new Runnable() {{
                        @Override
                        public void run() {{
                            if (webView != null) {{
                                webView.getSettings().setCacheMode(WebSettings.LOAD_DEFAULT);
                            }}
                        }}
                    }}, 2500);
                }} catch (Exception ignored) {{}}
            }}
        }});
    }}

    public void refreshPage() {{
        runOnUiThread(new Runnable() {{
            @Override
            public void run() {{
                if (webView == null) return;
                if (isShowingOffline || (webView.getUrl() != null && webView.getUrl().contains("offline.html"))) {{
                    retryConnection();
                }} else {{
                    if (progressBar != null) progressBar.setVisibility(View.VISIBLE);
                    String cur = webView.getUrl();
                    if (cur != null && !cur.isEmpty() && !cur.equals("about:blank") && !cur.contains("offline.html")) {{
                        try {{
                            webView.stopLoading();
                            webView.getSettings().setCacheMode(WebSettings.LOAD_NO_CACHE);
                            webView.reload();
                            webView.postDelayed(new Runnable() {{
                                @Override
                                public void run() {{
                                    if (webView != null) {{
                                        webView.getSettings().setCacheMode(WebSettings.LOAD_DEFAULT);
                                    }}
                                }}
                            }}, 2500);
                        }} catch (Exception e) {{
                            retryConnection();
                        }}
                    }} else {{
                        retryConnection();
                    }}
                }}
            }}
        }});
    }}

    private void showOfflinePage(String failingUrl) {{
        if (TARGET_URL != null && TARGET_URL.startsWith("file:///android_asset/") &&
            (failingUrl == null || failingUrl.startsWith("file:///android_asset/"))) {{
            return;
        }}
        if (failingUrl != null && !failingUrl.isEmpty() && !failingUrl.contains("offline.html")) {{
            lastFailedUrl = failingUrl;
        }}
        runOnUiThread(new Runnable() {{
            @Override
            public void run() {{
                if (webView != null) {{
                    if (isShowingOffline || (webView.getUrl() != null && webView.getUrl().contains("offline.html"))) {{
                        isShowingOffline = true;
                        webView.evaluateJavascript("if (typeof window.onRetryFailed === 'function') window.onRetryFailed();", null);
                        return;
                    }}
                    isShowingOffline = true;
                    String safeTarget = (lastFailedUrl != null && !lastFailedUrl.isEmpty() && !lastFailedUrl.contains("offline.html")) ? lastFailedUrl : TARGET_URL;
                    String offlineUrl = "file:///android_asset/offline.html?target_url=" + Uri.encode(safeTarget) + "#" + Uri.encode(safeTarget);
                    webView.loadUrl(offlineUrl);
                }}
            }}
        }});
    }}

    public boolean isNetworkAvailable() {{
        try {{
            ConnectivityManager cm = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
            if (cm != null) {{
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {{
                    Network activeNetwork = cm.getActiveNetwork();
                    if (activeNetwork != null) {{
                        NetworkCapabilities capabilities = cm.getNetworkCapabilities(activeNetwork);
                        return capabilities != null && (
                            capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) ||
                            capabilities.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) ||
                            capabilities.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET)
                        );
                    }}
                }} else {{
                    NetworkInfo activeNetworkInfo = cm.getActiveNetworkInfo();
                    return activeNetworkInfo != null && activeNetworkInfo.isConnected();
                }}
            }}
        }} catch (Exception ignored) {{}}
        return false;
    }}

    private void registerNetworkCallback() {{
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {{
            try {{
                ConnectivityManager cm = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
                if (cm != null) {{
                    networkCallback = new ConnectivityManager.NetworkCallback() {{
                        @Override
                        public void onAvailable(Network network) {{
                            runOnUiThread(new Runnable() {{
                                @Override
                                public void run() {{
                                    if (isShowingOffline || (webView != null && webView.getUrl() != null && webView.getUrl().contains("offline.html"))) {{
                                        retryConnection();
                                    }}
                                }}
                            }});
                        }}
                    }};
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {{
                        cm.registerDefaultNetworkCallback(networkCallback);
                    }} else {{
                        NetworkRequest request = new NetworkRequest.Builder()
                            .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
                            .build();
                        cm.registerNetworkCallback(request, networkCallback);
                    }}
                }}
            }} catch (Exception ignored) {{}}
        }}
    }}

    private void unregisterNetworkCallback() {{
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP && networkCallback != null) {{
            try {{
                ConnectivityManager cm = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
                if (cm != null) {{
                    cm.unregisterNetworkCallback(networkCallback);
                }}
            }} catch (Exception ignored) {{}}
            networkCallback = null;
        }}
    }}

    private void initVirtualMouse() {{
        tvMouseContainer = findViewById(R.id.tvMouseContainer);
        tvMouseClickRing = findViewById(R.id.tvMouseClickRing);
        tvMouseCursor = findViewById(R.id.tvMouseCursor);

        isTvDevice = checkIsTvDevice();
        if (isTvDevice) {{
            isMouseMode = true;
            if (tvMouseContainer != null) {{
                tvMouseContainer.bringToFront();
                tvMouseContainer.setVisibility(View.VISIBLE);
                tvMouseContainer.setAlpha(1.0f);
            }}
        }}

        if (webView != null) {{
            webView.post(new Runnable() {{
                @Override
                public void run() {{
                    initCursorPosition();
                }}
            }});
        }}
    }}

    private boolean checkIsTvDevice() {{
        if ({str(is_tv).lower()}) {{
            return true;
        }}
        try {{
            PackageManager pm = getPackageManager();
            if (pm != null && (pm.hasSystemFeature(PackageManager.FEATURE_LEANBACK) ||
                pm.hasSystemFeature("android.software.leanback") ||
                pm.hasSystemFeature("android.hardware.type.television") ||
                !pm.hasSystemFeature(PackageManager.FEATURE_TOUCHSCREEN))) {{
                return true;
            }}
        }} catch (Exception ignored) {{}}
        try {{
            UiModeManager uiModeManager = (UiModeManager) getSystemService(Context.UI_MODE_SERVICE);
            if (uiModeManager != null && uiModeManager.getCurrentModeType() == Configuration.UI_MODE_TYPE_TELEVISION) {{
                return true;
            }}
        }} catch (Exception ignored) {{}}
        try {{
            String model = Build.MODEL != null ? Build.MODEL.toLowerCase() : "";
            String device = Build.DEVICE != null ? Build.DEVICE.toLowerCase() : "";
            String product = Build.PRODUCT != null ? Build.PRODUCT.toLowerCase() : "";
            if (model.contains("tv") || model.contains("box") || model.contains("fire") ||
                device.contains("tv") || device.contains("box") || device.contains("aft") ||
                product.contains("tv") || product.contains("box")) {{
                return true;
            }}
        }} catch (Exception ignored) {{}}
        return false;
    }}

    private void initCursorPosition() {{
        if (cursorPositionInitialized) return;
        int w = (webView != null && webView.getWidth() > 0) ? webView.getWidth() : getResources().getDisplayMetrics().widthPixels;
        int h = (webView != null && webView.getHeight() > 0) ? webView.getHeight() : getResources().getDisplayMetrics().heightPixels;
        cursorX = w / 2f;
        cursorY = h / 2f;
        cursorPositionInitialized = true;
        updateCursorView();
        if (isMouseMode && tvMouseContainer != null) {{
            tvMouseContainer.bringToFront();
            tvMouseContainer.setVisibility(View.VISIBLE);
            tvMouseContainer.setAlpha(1.0f);
        }}
    }}

    private void updateCursorView() {{
        if (tvMouseContainer != null) {{
            tvMouseContainer.setTranslationX(cursorX);
            tvMouseContainer.setTranslationY(cursorY);
        }}
    }}

    public void showMouseCursor() {{
        isMouseMode = true;
        if (!cursorPositionInitialized) {{
            initCursorPosition();
        }}
        if (tvMouseContainer != null && tvMouseContainer.getVisibility() != View.VISIBLE) {{
            tvMouseContainer.setVisibility(View.VISIBLE);
            tvMouseContainer.setAlpha(0f);
            tvMouseContainer.animate().alpha(1f).setDuration(150).start();
        }}
    }}

    public void hideMouseCursor() {{
        if (tvMouseContainer != null && tvMouseContainer.getVisibility() == View.VISIBLE) {{
            tvMouseContainer.animate().alpha(0f).setDuration(150).withEndAction(new Runnable() {{
                @Override
                public void run() {{
                    if (tvMouseContainer != null) {{
                        tvMouseContainer.setVisibility(View.GONE);
                    }}
                }}
            }}).start();
        }}
        isMouseMode = false;
    }}

    public void toggleMouseMode() {{
        isMouseMode = !isMouseMode;
        if (isMouseMode) {{
            showMouseCursor();
            Toast.makeText(this, "TV Mouse: ON", Toast.LENGTH_SHORT).show();
        }} else {{
            hideMouseCursor();
            Toast.makeText(this, "TV Mouse: OFF", Toast.LENGTH_SHORT).show();
        }}
    }}

    private boolean moveMouseCursor(float dx, float dy, int repeatCount) {{
        showMouseCursor();

        float speedMultiplier = 1.0f;
        if (repeatCount > 0) {{
            speedMultiplier = Math.min(1.0f + (repeatCount * 0.25f), MAX_CURSOR_SPEED / BASE_CURSOR_SPEED);
        }}
        float moveX = dx * speedMultiplier;
        float moveY = dy * speedMultiplier;

        int screenW = (webView != null && webView.getWidth() > 0) ? webView.getWidth() : getResources().getDisplayMetrics().widthPixels;
        int screenH = (webView != null && webView.getHeight() > 0) ? webView.getHeight() : getResources().getDisplayMetrics().heightPixels;

        if (cursorY <= 30 && moveY < 0) {{
            if (webView != null) webView.scrollBy(0, (int) moveY * 2);
        }} else if (cursorY >= screenH - 50 && moveY > 0) {{
            if (webView != null) webView.scrollBy(0, (int) moveY * 2);
        }}

        cursorX = Math.max(0f, Math.min(cursorX + moveX, screenW - 10f));
        cursorY = Math.max(0f, Math.min(cursorY + moveY, screenH - 10f));

        updateCursorView();
        dispatchHover(cursorX, cursorY);
        return true;
    }}

    private void dispatchHover(float x, float y) {{
        if (webView == null || Build.VERSION.SDK_INT < Build.VERSION_CODES.ICE_CREAM_SANDWICH) return;
        try {{
            long now = SystemClock.uptimeMillis();
            MotionEvent hover = MotionEvent.obtain(now, now, MotionEvent.ACTION_HOVER_MOVE, x, y, 0);
            hover.setSource(InputDevice.SOURCE_CLASS_POINTER);
            webView.dispatchGenericMotionEvent(hover);
            hover.recycle();
        }} catch (Exception ignored) {{}}
    }}

    private void performMouseClick() {{
        showMouseCursor();
        if (webView == null) return;

        if (tvMouseCursor != null) {{
            tvMouseCursor.animate().scaleX(0.8f).scaleY(0.8f).setDuration(60).withEndAction(new Runnable() {{
                @Override
                public void run() {{
                    if (tvMouseCursor != null) {{
                        tvMouseCursor.animate().scaleX(1.0f).scaleY(1.0f).setDuration(60).start();
                    }}
                }}
            }}).start();
        }}
        if (tvMouseClickRing != null) {{
            tvMouseClickRing.setVisibility(View.VISIBLE);
            tvMouseClickRing.setScaleX(0.5f);
            tvMouseClickRing.setScaleY(0.5f);
            tvMouseClickRing.setAlpha(1.0f);
            tvMouseClickRing.animate()
                .scaleX(1.8f).scaleY(1.8f).alpha(0f)
                .setDuration(200)
                .withEndAction(new Runnable() {{
                    @Override
                    public void run() {{
                        if (tvMouseClickRing != null) {{
                            tvMouseClickRing.setVisibility(View.GONE);
                        }}
                    }}
                }}).start();
        }}

        int[] loc = new int[2];
        webView.getLocationOnScreen(loc);
        final float targetX = Math.max(0, cursorX - loc[0]);
        final float targetY = Math.max(0, cursorY - loc[1]);

        final long downTime = SystemClock.uptimeMillis();
        try {{
            MotionEvent down = MotionEvent.obtain(downTime, downTime, MotionEvent.ACTION_DOWN, targetX, targetY, 0);
            down.setSource(InputDevice.SOURCE_TOUCHSCREEN);
            webView.dispatchTouchEvent(down);
            down.recycle();
        }} catch (Exception ignored) {{}}

        mouseHandler.postDelayed(new Runnable() {{
            @Override
            public void run() {{
                if (webView != null) {{
                    try {{
                        long upTime = SystemClock.uptimeMillis();
                        MotionEvent up = MotionEvent.obtain(downTime, upTime, MotionEvent.ACTION_UP, targetX, targetY, 0);
                        up.setSource(InputDevice.SOURCE_TOUCHSCREEN);
                        webView.dispatchTouchEvent(up);
                        up.recycle();
                    }} catch (Exception ignored) {{}}
                }}
            }}
        }}, 80);
    }}

    @SuppressLint({{"SetJavaScriptEnabled"}})
    @Override
    protected void onCreate(Bundle savedInstanceState) {{
        super.onCreate(savedInstanceState);

        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        
        try {{
            getWindow().addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS);
            getWindow().setStatusBarColor(Color.parseColor("{clean_theme}"));
            getWindow().setNavigationBarColor(Color.parseColor("{clean_theme}"));
        }} catch (Exception ignored) {{}}

        setContentView(R.layout.activity_main);

        webView = findViewById(R.id.webview);
        progressBar = findViewById(R.id.progressBar);
        customViewContainer = findViewById(R.id.customViewContainer);
        originalOrientation = getRequestedOrientation();

        {fullscreen_code}

        WebSettings webSettings = webView.getSettings();
        webSettings.setJavaScriptEnabled(true);
        webSettings.setDomStorageEnabled(true);
        webSettings.setDatabaseEnabled(true);
        webSettings.setAllowFileAccess(true);
        webSettings.setAllowContentAccess(true);
        webSettings.setAllowFileAccessFromFileURLs(true);
        webSettings.setAllowUniversalAccessFromFileURLs(true);
        webSettings.setMediaPlaybackRequiresUserGesture(false);
        webSettings.setJavaScriptCanOpenWindowsAutomatically(true);
        webSettings.setSupportMultipleWindows(true);
        webSettings.setUseWideViewPort(true);
        webSettings.setLoadWithOverviewMode(true);
        webSettings.setSupportZoom(true);
        webSettings.setBuiltInZoomControls(true);
        webSettings.setDisplayZoomControls(false);
        if (!isNetworkAvailable()) {{
            webSettings.setCacheMode(WebSettings.LOAD_CACHE_ELSE_NETWORK);
        }} else {{
            webSettings.setCacheMode(WebSettings.LOAD_DEFAULT);
        }}
        webSettings.setGeolocationEnabled(true);

        try {{
            webSettings.setGeolocationDatabasePath(getFilesDir().getPath());
        }} catch (Exception ignored) {{}}

        try {{
            webSettings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        }} catch (Exception ignored) {{}}

        try {{
            CookieManager cookieManager = CookieManager.getInstance();
            cookieManager.setAcceptCookie(true);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {{
                cookieManager.setAcceptThirdPartyCookies(webView, true);
            }}
        }} catch (Exception ignored) {{}}

        try {{
            String defaultUa = webSettings.getUserAgentString();
            if (defaultUa != null) {{
                String cleanUa = defaultUa.replace("; wv", "").replaceAll("Version/\\\\d+\\\\.\\\\d+\\\\s*", "");
                webSettings.setUserAgentString(cleanUa);
            }}
        }} catch (Exception ignored) {{}}

        webView.setLayerType(View.LAYER_TYPE_HARDWARE, null);
        webView.setFocusable(true);
        webView.setFocusableInTouchMode(true);

        appInterface = new WebAppInterface();
        webView.addJavascriptInterface(appInterface, "AndroidApp");
        webView.addJavascriptInterface(appInterface, "AndroidBridge");

        try {{
            if (Build.VERSION.SDK_INT >= 33) {{
                registerBackInvokedCallback();
            }}
        }} catch (Throwable ignored) {{}}

        try {{
            registerNetworkCallback();
        }} catch (Throwable ignored) {{}}

        try {{
            initVirtualMouse();
        }} catch (Throwable ignored) {{}}

        webView.setOnTouchListener(new View.OnTouchListener() {{
            @Override
            public boolean onTouch(View v, MotionEvent event) {{
                switch (event.getAction()) {{
                    case MotionEvent.ACTION_DOWN:
                        touchDownY = event.getY();
                        touchDownX = event.getX();
                        isPullRefreshing = false;
                        if (!isTvDevice && isMouseMode) {{
                            hideMouseCursor();
                        }}
                        break;
                    case MotionEvent.ACTION_MOVE:
                        if (webView != null && webView.getScrollY() > 0) {{
                            touchDownY = event.getY();
                            touchDownX = event.getX();
                        }} else if (webView != null && webView.getScrollY() <= 0) {{
                            float deltaY = event.getY() - touchDownY;
                            float deltaX = Math.abs(event.getX() - touchDownX);
                            float density = getResources().getDisplayMetrics().density;
                            float pullThreshold = Math.max(120f, density * 75f);
                            if (deltaY > pullThreshold && deltaY > deltaX * 1.5f && !isPullRefreshing) {{
                                isPullRefreshing = true;
                                Toast.makeText(MainActivity.this, "Refreshing...", Toast.LENGTH_SHORT).show();
                                refreshPage();
                                v.postDelayed(new Runnable() {{
                                    @Override
                                    public void run() {{
                                        isPullRefreshing = false;
                                    }}
                                }}, 1500);
                            }}
                        }}
                        break;
                    case MotionEvent.ACTION_UP:
                    case MotionEvent.ACTION_CANCEL:
                        isPullRefreshing = false;
                        break;
                }}
                return false;
            }}
        }});

        webView.setDownloadListener(new DownloadListener() {{
            @Override
            public void onDownloadStart(String url, String userAgent, String contentDisposition, String mimetype, long contentLength) {{
                try {{
                    if (url.startsWith("blob:")) {{
                        String js = "(function() {{" +
                            "  try {{" +
                            "    fetch('" + url + "').then(function(r) {{ return r.blob(); }}).then(function(b) {{" +
                            "      var reader = new FileReader();" +
                            "      reader.onloadend = function() {{" +
                            "        if (window.AndroidApp && typeof window.AndroidApp.saveBase64File === 'function') {{" +
                            "          window.AndroidApp.saveBase64File(reader.result, 'database_export.sqlite', b.type || '" + (mimetype != null ? mimetype : "") + "');" +
                            "        }}" +
                            "      }};" +
                            "      reader.readAsDataURL(b);" +
                            "    }}).catch(function(err) {{ console.error('Blob fetch failed', err); }});" +
                            "  }} catch(e) {{ console.error(e); }}" +
                            "}})();";
                        webView.evaluateJavascript(js, null);
                        return;
                    }}
                    if (url.startsWith("data:")) {{
                        if (appInterface != null) {{
                            appInterface.saveBase64File(url, "database_export", mimetype);
                        }}
                        return;
                    }}
                    String fileName = null;
                    if (contentDisposition != null) {{
                        java.util.regex.Matcher m = java.util.regex.Pattern.compile("filename\\*?=['\"]?(?:UTF-8'')?([^;'\"]+)['\"]?", java.util.regex.Pattern.CASE_INSENSITIVE).matcher(contentDisposition);
                        if (m.find()) {{
                            fileName = m.group(1).trim();
                        }}
                    }}
                    if (fileName == null || fileName.isEmpty()) {{
                        fileName = URLUtil.guessFileName(url, contentDisposition, mimetype);
                    }}
                    String urlLower = url.toLowerCase();
                    if (fileName.endsWith(".html") || fileName.endsWith(".bin") || !fileName.contains(".")) {{
                        if (urlLower.contains(".sqlite3")) fileName = fileName.replaceAll("\\.[^.]+$", "") + ".sqlite3";
                        else if (urlLower.contains(".sqlite")) fileName = fileName.replaceAll("\\.[^.]+$", "") + ".sqlite";
                        else if (urlLower.contains(".db3")) fileName = fileName.replaceAll("\\.[^.]+$", "") + ".db3";
                        else if (urlLower.contains(".db")) fileName = fileName.replaceAll("\\.[^.]+$", "") + ".db";
                        else if (urlLower.contains(".sql")) fileName = fileName.replaceAll("\\.[^.]+$", "") + ".sql";
                        else if (urlLower.contains(".json")) fileName = fileName.replaceAll("\\.[^.]+$", "") + ".json";
                        else if (urlLower.contains(".csv")) fileName = fileName.replaceAll("\\.[^.]+$", "") + ".csv";
                        else if (urlLower.contains(".xlsx")) fileName = fileName.replaceAll("\\.[^.]+$", "") + ".xlsx";
                        else if (urlLower.contains(".zip")) fileName = fileName.replaceAll("\\.[^.]+$", "") + ".zip";
                    }}
                    DownloadManager.Request request = new DownloadManager.Request(Uri.parse(url));
                    if (mimetype != null && !mimetype.isEmpty()) {{
                        request.setMimeType(mimetype);
                    }}
                    String cookies = CookieManager.getInstance().getCookie(url);
                    if (cookies != null) {{
                        request.addRequestHeader("cookie", cookies);
                    }}
                    if (userAgent != null) {{
                        request.addRequestHeader("User-Agent", userAgent);
                    }}
                    request.setTitle(fileName);
                    request.setDescription("Downloading " + fileName);
                    request.allowScanningByMediaScanner();
                    request.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);
                    request.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS, fileName);
                    DownloadManager dm = (DownloadManager) getSystemService(DOWNLOAD_SERVICE);
                    if (dm != null) {{
                        dm.enqueue(request);
                        Toast.makeText(MainActivity.this, "Downloading: " + fileName, Toast.LENGTH_SHORT).show();
                    }}
                }} catch (Exception e) {{
                    try {{
                        Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                        startActivity(intent);
                    }} catch (Exception ignored) {{}}
                }}
            }}
        }});

        webView.setWebViewClient(new WebViewClient() {{
            @Override
            public void onPageStarted(WebView view, String url, Bitmap favicon) {{
                if (progressBar != null) progressBar.setVisibility(View.VISIBLE);
                if (url != null && !url.contains("offline.html")) {{
                    isShowingOffline = false;
                    lastFailedUrl = url;
                }}
                super.onPageStarted(view, url, favicon);
            }}

            @Override
            public void onPageFinished(WebView view, String url) {{
                if (progressBar != null) progressBar.setVisibility(View.GONE);
                if (url != null && !url.contains("offline.html")) {{
                    isShowingOffline = false;
                }} else if (url != null && url.contains("offline.html")) {{
                    isShowingOffline = true;
                }}
                isPullRefreshing = false;
                try {{
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {{
                        CookieManager.getInstance().flush();
                    }}
                }} catch (Exception ignored) {{}}
                try {{
                    view.evaluateJavascript(
                        "(function() {{" +
                        "  var iframes = document.querySelectorAll('iframe');" +
                        "  for (var i = 0; i < iframes.length; i++) {{" +
                        "    iframes[i].setAttribute('allowfullscreen', 'true');" +
                        "    iframes[i].setAttribute('webkitallowfullscreen', 'true');" +
                        "    var a = iframes[i].getAttribute('allow') || '';" +
                        "    if (a.indexOf('fullscreen') === -1) {{" +
                        "      iframes[i].setAttribute('allow', (a ? a + '; ' : '') + 'fullscreen; autoplay; encrypted-media; picture-in-picture');" +
                        "    }}" +
                        "  }}" +
                        "  if (!document.getElementById('web2apk-injected-lights-css')) {{" +
                        "    var st = document.createElement('style');" +
                        "    st.id = 'web2apk-injected-lights-css';" +
                        "    st.textContent = 'video, iframe[src*=embed], iframe[src*=player], iframe[allowfullscreen], .jwplayer, .video-js, .plyr, [class*=player], [id*=player] {{ position: relative !important; z-index: 2147483640 !important; }}';" +
                        "    (document.head || document.documentElement).appendChild(st);" +
                        "  }}" +
                        "  if (window.Web2APK && typeof window.Web2APK.initLightsOutHealer === 'function') {{" +
                        "    window.Web2APK.initLightsOutHealer();" +
                        "  }}" +
                        "}})();", null);
                try {{
                    view.evaluateJavascript(
                        "(function() {{" +
                        "  if (window.__web2apk_download_interceptor) return;" +
                        "  window.__web2apk_download_interceptor = true;" +
                        "  window.__blob_cache = window.__blob_cache || {{}};" +
                        "  try {{" +
                        "    var origCreate = URL.createObjectURL;" +
                        "    if (origCreate) {{" +
                        "      URL.createObjectURL = function(blob) {{" +
                        "        var u = origCreate.call(URL, blob);" +
                        "        window.__blob_cache[u] = blob;" +
                        "        return u;" +
                        "      }};" +
                        "    }}" +
                        "    var origRevoke = URL.revokeObjectURL;" +
                        "    if (origRevoke) {{" +
                        "      URL.revokeObjectURL = function(u) {{" +
                        "        setTimeout(function() {{" +
                        "          delete window.__blob_cache[u];" +
                        "          try {{ origRevoke.call(URL, u); }} catch(e){{}}" +
                        "        }}, 30000);" +
                        "      }};" +
                        "    }}" +
                        "  }} catch(e) {{}}" +
                        "  var dbExts = ['.sqlite','.sqlite3','.db','.db3','.s3db','.sl3','.sql','.dump','.bak','.backup','.json','.csv','.tsv','.xlsx','.xls','.xml','.parquet','.zip','.tar','.gz','.7z','.rar','.bin','.dat','.pdf','.txt'];" +
                        "  function isDb(u, f) {{" +
                        "    var s = ((f || '') + ' ' + (u || '')).toLowerCase();" +
                        "    for (var i = 0; i < dbExts.length; i++) {{ if (s.indexOf(dbExts[i]) !== -1) return true; }}" +
                        "    return false;" +
                        "  }}" +
                        "  function procBlob(b, name) {{" +
                        "    var reader = new FileReader();" +
                        "    reader.onloadend = function() {{" +
                        "      if (window.AndroidApp && window.AndroidApp.saveBase64File) window.AndroidApp.saveBase64File(reader.result, name || 'database.sqlite', b.type || '');" +
                        "      else if (window.AndroidBridge && window.AndroidBridge.saveBase64File) window.AndroidBridge.saveBase64File(reader.result, name || 'database.sqlite', b.type || '');" +
                        "    }};" +
                        "    reader.readAsDataURL(b);" +
                        "  }}" +
                        "  function trig(u, name) {{" +
                        "    if (!u) return false;" +
                        "    if (u.indexOf('blob:') === 0) {{" +
                        "      var cached = (window.__blob_cache && window.__blob_cache[u]) ? window.__blob_cache[u] : null;" +
                        "      if (cached) {{" +
                        "        procBlob(cached, name);" +
                        "      }} else {{" +
                        "        fetch(u).then(function(r) {{ return r.blob(); }}).then(function(b) {{ procBlob(b, name); }}).catch(function() {{}});" +
                        "      }}" +
                        "      return true;" +
                        "    }} else if (u.indexOf('data:') === 0) {{" +
                        "      if (window.AndroidApp && window.AndroidApp.saveBase64File) {{ window.AndroidApp.saveBase64File(u, name || 'database.sqlite', ''); return true; }}" +
                        "    }} else if (isDb(u, name) || name) {{" +
                        "      if (window.AndroidApp && window.AndroidApp.downloadUrlWithFilename) {{ window.AndroidApp.downloadUrlWithFilename(u, name || '', ''); return true; }}" +
                        "    }}" +
                        "    return false;" +
                        "  }}" +
                        "  document.addEventListener('click', function(e) {{" +
                        "    var t = e.target;" +
                        "    while (t && t.tagName !== 'A') t = t.parentElement;" +
                        "    if (!t || t.tagName !== 'A') return;" +
                        "    var h = t.getAttribute('href') || t.href || '';" +
                        "    var d = t.getAttribute('download');" +
                        "    var fn = d || t.download || '';" +
                        "    if (d !== null || h.indexOf('blob:') === 0 || h.indexOf('data:') === 0 || isDb(h, fn)) {{" +
                        "      if (trig(h, fn)) {{ e.preventDefault(); e.stopPropagation(); }}" +
                        "    }}" +
                        "  }}, true);" +
                        "  try {{" +
                        "    var origClick = HTMLAnchorElement.prototype.click;" +
                        "    HTMLAnchorElement.prototype.click = function() {{" +
                        "      var h = this.getAttribute('href') || this.href || '';" +
                        "      var d = this.getAttribute('download');" +
                        "      var fn = d || this.download || '';" +
                        "      if (d !== null || h.indexOf('blob:') === 0 || h.indexOf('data:') === 0 || isDb(h, fn)) {{" +
                        "        if (trig(h, fn)) return;" +
                        "      }}" +
                        "      return origClick.apply(this, arguments);" +
                        "    }};" +
                        "  }} catch(e) {{}}" +
                        "}})();", null);
                }} catch (Exception ignored) {{}}
                super.onPageFinished(view, url);
            }}

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {{
                if (request != null && request.isForMainFrame()) {{
                    String failed = (request.getUrl() != null) ? request.getUrl().toString() : (lastFailedUrl != null ? lastFailedUrl : TARGET_URL);
                    showOfflinePage(failed);
                }}
            }}

            @Override
            public void onReceivedError(WebView view, int errorCode, String description, String failingUrl) {{
                if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) {{
                    if (failingUrl != null) {{
                        String lower = failingUrl.toLowerCase();
                        if (lower.endsWith(".png") || lower.endsWith(".jpg") || lower.endsWith(".jpeg") ||
                            lower.endsWith(".gif") || lower.endsWith(".svg") || lower.endsWith(".webp") ||
                            lower.endsWith(".css") || lower.endsWith(".js") || lower.endsWith(".ico") ||
                            lower.endsWith(".woff") || lower.endsWith(".woff2") || lower.endsWith(".ttf")) {{
                            return;
                        }}
                        if (failingUrl.equals(TARGET_URL) || failingUrl.equals(lastFailedUrl) ||
                            (view != null && view.getUrl() != null && view.getUrl().equals(failingUrl))) {{
                            showOfflinePage(failingUrl);
                        }}
                    }}
                }}
            }}

            @Override
            public void onReceivedHttpError(WebView view, WebResourceRequest request, WebResourceResponse errorResponse) {{
                if (request != null && request.isForMainFrame() && errorResponse != null) {{
                    int code = errorResponse.getStatusCode();
                    if (code >= 500 && code < 600) {{
                        String failed = (request.getUrl() != null) ? request.getUrl().toString() : TARGET_URL;
                        showOfflinePage(failed);
                    }}
                }}
            }}

            @Override
            public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {{
                super.onReceivedSslError(view, handler, error);
            }}

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {{
                String url = request.getUrl().toString();
                String lowerUrl = url.toLowerCase();
                if (lowerUrl.endsWith(".sqlite") || lowerUrl.endsWith(".sqlite3") || lowerUrl.endsWith(".db") || lowerUrl.endsWith(".db3") ||
                    lowerUrl.endsWith(".sql") || lowerUrl.endsWith(".dump") || lowerUrl.endsWith(".bak") || lowerUrl.endsWith(".parquet") ||
                    lowerUrl.endsWith(".csv") || lowerUrl.endsWith(".tsv") || lowerUrl.endsWith(".xlsx") || lowerUrl.endsWith(".zip")) {{
                    if (appInterface != null) {{
                        String guessed = URLUtil.guessFileName(url, null, null);
                        appInterface.downloadUrlWithFilename(url, guessed, "");
                        return true;
                    }}
                }}
                if (url.startsWith("http://") || url.startsWith("https://") || url.startsWith("file:///android_asset/")) {{
                    return false;
                }}
                if (url.startsWith("intent://")) {{
                    try {{
                        Intent intent = Intent.parseUri(url, Intent.URI_INTENT_SCHEME);
                        if (intent != null) {{
                            if (getPackageManager().resolveActivity(intent, 0) != null) {{
                                startActivity(intent);
                                return true;
                            }}
                            String fallbackUrl = intent.getStringExtra("browser_fallback_url");
                            if (fallbackUrl != null && !fallbackUrl.isEmpty()) {{
                                view.loadUrl(fallbackUrl);
                                return true;
                            }}
                            String packageName = intent.getPackage();
                            if (packageName != null && !packageName.isEmpty()) {{
                                Intent marketIntent = new Intent(Intent.ACTION_VIEW, Uri.parse("market://details?id=" + packageName));
                                startActivity(marketIntent);
                                return true;
                            }}
                        }}
                    }} catch (Exception ignored) {{}}
                }}
                try {{
                    Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                    startActivity(intent);
                    return true;
                }} catch (Exception e) {{
                    return false;
                }}
            }}
        }});

        webChromeClient = new WebChromeClient() {{
            @Override
            public void onProgressChanged(WebView view, int newProgress) {{
                if (progressBar != null) {{
                    progressBar.setProgress(newProgress);
                    if (newProgress == 100) {{
                        progressBar.setVisibility(View.GONE);
                    }}
                }}
            }}

            @Override
            public boolean onConsoleMessage(ConsoleMessage consoleMessage) {{
                return true;
            }}

            @Override
            public void onGeolocationPermissionsShowPrompt(String origin, GeolocationPermissions.Callback callback) {{
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {{
                    if (checkSelfPermission(android.Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {{
                        pendingGeoOrigin = origin;
                        pendingGeoCallback = callback;
                        requestPermissions(new String[]{{android.Manifest.permission.ACCESS_FINE_LOCATION, android.Manifest.permission.ACCESS_COARSE_LOCATION}}, PERMISSIONS_REQUEST_LOCATION);
                        return;
                    }}
                }}
                callback.invoke(origin, true, false);
            }}

            @Override
            public boolean onCreateWindow(WebView view, boolean isDialog, boolean isUserGesture, Message resultMsg) {{
                WebView tempWebView = new WebView(MainActivity.this);
                tempWebView.setWebViewClient(new WebViewClient() {{
                    @Override
                    public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest req) {{
                        webView.loadUrl(req.getUrl().toString());
                        return true;
                    }}
                }});
                WebView.WebViewTransport transport = (WebView.WebViewTransport) resultMsg.obj;
                transport.setWebView(tempWebView);
                resultMsg.sendToTarget();
                return true;
            }}

            @Override
            public void onShowCustomView(View view, CustomViewCallback callback) {{
                if (customView != null) {{
                    onHideCustomView();
                    return;
                }}
                customView = view;
                customViewCallback = callback;
                originalOrientation = getRequestedOrientation();
                originalSystemUiVisibility = getWindow().getDecorView().getSystemUiVisibility();

                if (webView != null) webView.setVisibility(View.GONE);
                if (progressBar != null) progressBar.setVisibility(View.GONE);

                if (customViewContainer != null) {{
                    customViewContainer.setVisibility(View.VISIBLE);
                    customViewContainer.addView(view, new FrameLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.MATCH_PARENT
                    ));
                }}

                getWindow().getDecorView().setSystemUiVisibility(
                    View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                    | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                    | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                    | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                    | View.SYSTEM_UI_FLAG_FULLSCREEN
                    | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                );

                try {{
                    setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE);
                }} catch (Exception ignored) {{}}
            }}

            @Override
            public void onHideCustomView() {{
                if (customView == null) return;

                if (customViewContainer != null) {{
                    customViewContainer.removeView(customView);
                    customViewContainer.setVisibility(View.GONE);
                }}
                customView = null;

                if (webView != null) webView.setVisibility(View.VISIBLE);

                if (customViewCallback != null) {{
                    customViewCallback.onCustomViewHidden();
                    customViewCallback = null;
                }}

                getWindow().getDecorView().setSystemUiVisibility(originalSystemUiVisibility);
                try {{
                    setRequestedOrientation(originalOrientation);
                }} catch (Exception ignored) {{}}
            }}

            @Override
            public Bitmap getDefaultVideoPoster() {{
                return Bitmap.createBitmap(50, 50, Bitmap.Config.ARGB_8888);
            }}

            @Override
            public View getVideoLoadingProgressView() {{
                ProgressBar pb = new ProgressBar(MainActivity.this);
                pb.setIndeterminate(true);
                return pb;
            }}

            @Override
            public void onPermissionRequest(final PermissionRequest request) {{
                runOnUiThread(new Runnable() {{
                    @Override
                    public void run() {{
                        request.grant(request.getResources());
                    }}
                }});
            }}

            @Override
            public boolean onShowFileChooser(WebView webView, ValueCallback<Uri[]> filePathCallback,
                                            FileChooserParams fileChooserParams) {{
                if (uploadMessage != null) {{
                    uploadMessage.onReceiveValue(null);
                }}
                uploadMessage = filePathCallback;

                try {{
                    Intent intent = fileChooserParams.createIntent();
                    startActivityForResult(intent, FILECHOOSER_RESULTCODE);
                    return true;
                }} catch (Exception e) {{
                    try {{
                        Intent fallback = new Intent(Intent.ACTION_GET_CONTENT);
                        fallback.addCategory(Intent.CATEGORY_OPENABLE);
                        fallback.setType("*/*");
                        startActivityForResult(Intent.createChooser(fallback, "Select File"), FILECHOOSER_RESULTCODE);
                        return true;
                    }} catch (Exception ignored) {{}}
                    uploadMessage = null;
                    return false;
                }}
            }}
        }};

        webView.setWebChromeClient(webChromeClient);
        webView.loadUrl(TARGET_URL);
    }}

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {{
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == PERMISSIONS_REQUEST_LOCATION) {{
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {{
                if (pendingGeoCallback != null && pendingGeoOrigin != null) {{
                    pendingGeoCallback.invoke(pendingGeoOrigin, true, false);
                }}
            }} else {{
                if (pendingGeoCallback != null && pendingGeoOrigin != null) {{
                    pendingGeoCallback.invoke(pendingGeoOrigin, false, false);
                }}
            }}
            pendingGeoCallback = null;
            pendingGeoOrigin = null;
        }}
    }}

    @Override
    protected void onUserLeaveHint() {{
        super.onUserLeaveHint();
        if (customView != null && Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {{
            try {{
                if (getPackageManager().hasSystemFeature(PackageManager.FEATURE_PICTURE_IN_PICTURE)) {{
                    enterPictureInPictureMode();
                }}
            }} catch (Exception ignored) {{}}
        }}
    }}

    @Override
    protected void onPause() {{
        super.onPause();
        if (webView != null) {{
            webView.onPause();
            webView.pauseTimers();
        }}
        try {{
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {{
                CookieManager.getInstance().flush();
            }}
        }} catch (Exception ignored) {{}}
    }}

    @Override
    protected void onResume() {{
        super.onResume();
        if (webView != null) {{
            webView.onResume();
            webView.resumeTimers();
        }}
    }}

    @Override
    protected void onDestroy() {{
        unregisterNetworkCallback();
        if (customView != null && webChromeClient != null) {{
            webChromeClient.onHideCustomView();
        }}
        if (webView != null) {{
            webView.loadUrl("about:blank");
            webView.stopLoading();
            webView.setWebChromeClient(null);
            webView.setWebViewClient(null);
            webView.destroy();
            webView = null;
        }}
        super.onDestroy();
    }}

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {{
        if (requestCode == FILECHOOSER_RESULTCODE) {{
            if (uploadMessage != null) {{
                uploadMessage.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(resultCode, data));
                uploadMessage = null;
            }}
        }}
        super.onActivityResult(requestCode, resultCode, data);
    }}

    @Override
    public boolean dispatchKeyEvent(KeyEvent event) {{
        int keyCode = event.getKeyCode();
        if (keyCode == KeyEvent.KEYCODE_BACK) {{
            if (event.getAction() == KeyEvent.ACTION_UP) {{
                handleBackPress();
            }}
            return true;
        }}

        if (isTvDevice || isMouseMode) {{
            int action = event.getAction();

            if (action == KeyEvent.ACTION_DOWN) {{
                switch (keyCode) {{
                    case KeyEvent.KEYCODE_DPAD_UP:
                    case KeyEvent.KEYCODE_DPAD_DOWN:
                    case KeyEvent.KEYCODE_DPAD_LEFT:
                    case KeyEvent.KEYCODE_DPAD_RIGHT:
                    case KeyEvent.KEYCODE_DPAD_CENTER:
                    case KeyEvent.KEYCODE_ENTER:
                    case KeyEvent.KEYCODE_NUMPAD_ENTER:
                    case KeyEvent.KEYCODE_BUTTON_A:
                    case KeyEvent.KEYCODE_PAGE_UP:
                    case KeyEvent.KEYCODE_CHANNEL_UP:
                    case KeyEvent.KEYCODE_PAGE_DOWN:
                    case KeyEvent.KEYCODE_CHANNEL_DOWN:
                    case KeyEvent.KEYCODE_INFO:
                    case KeyEvent.KEYCODE_GUIDE:
                    case KeyEvent.KEYCODE_BOOKMARK:
                    case KeyEvent.KEYCODE_MENU:
                    case KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE:
                    case KeyEvent.KEYCODE_REFRESH:
                    case KeyEvent.KEYCODE_F5:
                        return onKeyDown(keyCode, event);
                }}
            }} else if (action == KeyEvent.ACTION_UP) {{
                switch (keyCode) {{
                    case KeyEvent.KEYCODE_DPAD_UP:
                    case KeyEvent.KEYCODE_DPAD_DOWN:
                    case KeyEvent.KEYCODE_DPAD_LEFT:
                    case KeyEvent.KEYCODE_DPAD_RIGHT:
                    case KeyEvent.KEYCODE_DPAD_CENTER:
                    case KeyEvent.KEYCODE_ENTER:
                    case KeyEvent.KEYCODE_NUMPAD_ENTER:
                    case KeyEvent.KEYCODE_BUTTON_A:
                        return true;
                }}
            }}
        }}
        return super.dispatchKeyEvent(event);
    }}

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {{
        int repeat = event.getRepeatCount();

        switch (keyCode) {{
            case KeyEvent.KEYCODE_DPAD_UP:
                return moveMouseCursor(0, -BASE_CURSOR_SPEED, repeat);
            case KeyEvent.KEYCODE_DPAD_DOWN:
                return moveMouseCursor(0, BASE_CURSOR_SPEED, repeat);
            case KeyEvent.KEYCODE_DPAD_LEFT:
                return moveMouseCursor(-BASE_CURSOR_SPEED, 0, repeat);
            case KeyEvent.KEYCODE_DPAD_RIGHT:
                return moveMouseCursor(BASE_CURSOR_SPEED, 0, repeat);
            case KeyEvent.KEYCODE_DPAD_CENTER:
            case KeyEvent.KEYCODE_ENTER:
            case KeyEvent.KEYCODE_NUMPAD_ENTER:
            case KeyEvent.KEYCODE_BUTTON_A:
                if (isShowingOffline) {{
                    retryConnection();
                    return true;
                }}
                performMouseClick();
                return true;
            case KeyEvent.KEYCODE_PAGE_UP:
            case KeyEvent.KEYCODE_CHANNEL_UP:
                if (webView != null) webView.pageUp(false);
                return true;
            case KeyEvent.KEYCODE_PAGE_DOWN:
            case KeyEvent.KEYCODE_CHANNEL_DOWN:
                if (webView != null) webView.pageDown(false);
                return true;
            case KeyEvent.KEYCODE_INFO:
            case KeyEvent.KEYCODE_GUIDE:
            case KeyEvent.KEYCODE_BOOKMARK:
                toggleMouseMode();
                return true;
            case KeyEvent.KEYCODE_MENU:
            case KeyEvent.KEYCODE_MEDIA_PLAY_PAUSE:
            case KeyEvent.KEYCODE_REFRESH:
            case KeyEvent.KEYCODE_F5:
                Toast.makeText(MainActivity.this, "Refreshing...", Toast.LENGTH_SHORT).show();
                refreshPage();
                return true;
            case KeyEvent.KEYCODE_BACK:
                handleBackPress();
                return true;
        }}
        return super.onKeyDown(keyCode, event);
    }}

    @Override
    public boolean onGenericMotionEvent(MotionEvent event) {{
        if ((event.getSource() & InputDevice.SOURCE_JOYSTICK) == InputDevice.SOURCE_JOYSTICK &&
            event.getAction() == MotionEvent.ACTION_MOVE) {{
            float xVal = event.getAxisValue(MotionEvent.AXIS_X);
            float yVal = event.getAxisValue(MotionEvent.AXIS_Y);
            if (Math.abs(xVal) > 0.15f || Math.abs(yVal) > 0.15f) {{
                moveMouseCursor(xVal * BASE_CURSOR_SPEED * 1.5f, yVal * BASE_CURSOR_SPEED * 1.5f, 0);
                return true;
            }}
        }}
        return super.onGenericMotionEvent(event);
    }}

    @Override
    public void onBackPressed() {{
        handleBackPress();
    }}

    private void registerBackInvokedCallback() {{
        if (Build.VERSION.SDK_INT >= 33) {{
            try {{
                getOnBackInvokedDispatcher().registerOnBackInvokedCallback(
                    OnBackInvokedDispatcher.PRIORITY_DEFAULT,
                    new OnBackInvokedCallback() {{
                        @Override
                        public void onBackInvoked() {{
                            handleBackPress();
                        }}
                    }}
                );
            }} catch (Exception ignored) {{}}
        }}
    }}

    public void handleBackPress() {{
        long now = SystemClock.uptimeMillis();
        if (now - lastBackInvocationTime < 250) return;
        lastBackInvocationTime = now;

        runOnUiThread(new Runnable() {{
            @Override
            public void run() {{
                // 1. Fullscreen Custom View (e.g. HTML5 fullscreen video)
                if (customView != null) {{
                    if (webChromeClient != null) {{
                        webChromeClient.onHideCustomView();
                    }}
                    return;
                }}

                // 2. Synchronous Bridge check for Lights Out
                if (appInterface != null && appInterface.isLightsOutActive()) {{
                    appInterface.setLightsOutActive(false);
                    if (webView != null) {{
                        webView.evaluateJavascript(
                            "(function() {{" +
                            "  if (window.Web2APK && typeof window.Web2APK.dismissLightsOutOrModal === 'function') {{" +
                            "    return window.Web2APK.dismissLightsOutOrModal();" +
                            "  }} else if (typeof window.__web2apk_dismissLightsOut === 'function') {{" +
                            "    return window.__web2apk_dismissLightsOut();" +
                            "  }}" +
                            "  return false;" +
                            "}})();", null);
                    }}
                    Toast.makeText(MainActivity.this, "Lights restored", Toast.LENGTH_SHORT).show();
                    return;
                }}

                // 3. Query WebView JavaScript for active Lights Out, Cinema mode, or in-page modal
                if (webView != null) {{
                    webView.evaluateJavascript(
                        "(function() {{" +
                        "  if (window.Web2APK && typeof window.Web2APK.dismissLightsOutOrModal === 'function') {{" +
                        "    return window.Web2APK.dismissLightsOutOrModal();" +
                        "  }} else if (typeof window.__web2apk_dismissLightsOut === 'function') {{" +
                        "    return window.__web2apk_dismissLightsOut();" +
                        "  }}" +
                        "  return false;" +
                        "}})();",
                        new ValueCallback<String>() {{
                            @Override
                            public void onReceiveValue(String value) {{
                                if ("true".equalsIgnoreCase(value)) {{
                                    // Lights out or modal was successfully dismissed! Do not navigate away.
                                    Toast.makeText(MainActivity.this, "Lights restored", Toast.LENGTH_SHORT).show();
                                    return;
                                }}
                                proceedWithStandardBackNavigation();
                            }}
                        }}
                    );
                }} else {{
                    proceedWithStandardBackNavigation();
                }}
            }}
        }});
    }}

    private void proceedWithStandardBackNavigation() {{
        runOnUiThread(new Runnable() {{
            @Override
            public void run() {{
                // 4. Standard WebView History Navigation
                if (webView != null && webView.canGoBack() && !isShowingOffline) {{
                    try {{
                        WebBackForwardList history = webView.copyBackForwardList();
                        if (history != null && history.getCurrentIndex() > 0) {{
                            WebHistoryItem prevItem = history.getItemAtIndex(history.getCurrentIndex() - 1);
                            if (prevItem != null && prevItem.getUrl() != null && prevItem.getUrl().contains("offline.html")) {{
                                if (history.getCurrentIndex() >= 2) {{
                                    webView.goBackOrForward(-2);
                                    return;
                                }}
                            }}
                        }}
                    }} catch (Exception ignored) {{}}
                    webView.goBack();
                    return;
                }}

                // 5. If on offline page and can go back
                if (isShowingOffline && webView != null && webView.canGoBack()) {{
                    webView.goBack();
                    return;
                }}

                // 6. Double-tap back protection to prevent accidental app termination
                long currentTime = System.currentTimeMillis();
                if (currentTime - lastBackPressTime < BACK_PRESS_INTERVAL) {{
                    finish();
                }} else {{
                    lastBackPressTime = currentTime;
                    Toast.makeText(MainActivity.this, "Press back again to exit", Toast.LENGTH_SHORT).show();
                }}
            }}
        }});
    }}

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {{
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) {{
            if (!cursorPositionInitialized) {{
                initCursorPosition();
            }}
            if (customView != null) {{
                getWindow().getDecorView().setSystemUiVisibility(
                    View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                    | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                    | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                    | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                    | View.SYSTEM_UI_FLAG_FULLSCREEN
                    | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                );
            }} else {{
                {fullscreen_code}
            }}
        }}
    }}
}}
"""

    @staticmethod
    def _generate_res_files(res_dir: Path, app_name: str):
        values_dir = res_dir / "values"
        values_dir.mkdir(parents=True, exist_ok=True)
        safe_app_name = (app_name or "Web App").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "\\'").replace('"', '\\"')
        (values_dir / "strings.xml").write_text(f"""<resources>
    <string name="app_name">{safe_app_name}</string>
</resources>""", encoding="utf-8")

        (values_dir / "styles.xml").write_text("""<resources>
    <style name="Theme.Web2APK.Fullscreen" parent="@android:style/Theme.NoTitleBar.Fullscreen">
        <item name="android:windowBackground">@android:color/black</item>
        <item name="android:colorBackground">@android:color/black</item>
    </style>
</resources>""", encoding="utf-8")

        xml_dir = res_dir / "xml"
        xml_dir.mkdir(parents=True, exist_ok=True)
        (xml_dir / "network_security_config.xml").write_text("""<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <base-config cleartextTrafficPermitted="true">
        <trust-anchors>
            <certificates src="system" />
            <certificates src="user" />
        </trust-anchors>
    </base-config>
</network-security-config>""", encoding="utf-8")

        drawable_dir = res_dir / "drawable"
        drawable_dir.mkdir(parents=True, exist_ok=True)
        (drawable_dir / "ic_tv_mouse_cursor.xml").write_text("""<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="32dp"
    android:height="32dp"
    android:viewportWidth="32"
    android:viewportHeight="32">
    <!-- Drop Shadow -->
    <path
        android:fillColor="#55000000"
        android:pathData="M5,4 L5,26 L11,20 L15,29 L18,27.5 L14,19 L22,19 Z" />
    <!-- Outer Black Border -->
    <path
        android:fillColor="#000000"
        android:pathData="M3,2 L3,24 L9,18 L13,27 L16,25.5 L12,17 L20,17 Z" />
    <!-- Inner White Pointer Body -->
    <path
        android:fillColor="#FFFFFF"
        android:pathData="M4.5,4.5 L4.5,21.5 L8.5,17.5 L12.5,25.5 L14,24.5 L10.2,16.5 L17.5,16.5 Z" />
</vector>""", encoding="utf-8")

        # Also generate crisp PNG fallback in drawable-xhdpi for AOSP / older TV firmware
        drawable_xhdpi = res_dir / "drawable-xhdpi"
        drawable_xhdpi.mkdir(parents=True, exist_ok=True)
        try:
            from PIL import Image, ImageDraw
            cursor_img = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
            cdraw = ImageDraw.Draw(cursor_img)
            cdraw.polygon([(9, 7), (9, 37), (17, 29), (23, 43), (28, 41), (22, 27), (35, 27)], fill=(0, 0, 0, 120))
            cdraw.polygon([(6, 4), (6, 34), (14, 26), (20, 40), (25, 38), (19, 24), (32, 24)], fill=(0, 0, 0, 255))
            cdraw.polygon([(8, 7), (8, 30), (14, 24), (19, 36), (22, 35), (17, 23), (28, 23)], fill=(255, 255, 255, 255))
            cursor_img.save(drawable_xhdpi / "ic_tv_mouse_cursor.png", "PNG")
        except Exception:
            pass

        (drawable_dir / "tv_mouse_click_ring.xml").write_text("""<shape xmlns:android="http://schemas.android.com/apk/res/android"
    android:shape="oval">
    <stroke
        android:width="2dp"
        android:color="#38bdf8" />
    <solid
        android:color="#4438bdf8" />
</shape>""", encoding="utf-8")

        layout_dir = res_dir / "layout"
        layout_dir.mkdir(parents=True, exist_ok=True)
        (layout_dir / "activity_main.xml").write_text("""<?xml version="1.0" encoding="utf-8"?>
<RelativeLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:background="#000000">

    <WebView
        android:id="@+id/webview"
        android:layout_width="match_parent"
        android:layout_height="match_parent" />

    <FrameLayout
        android:id="@+id/customViewContainer"
        android:layout_width="match_parent"
        android:layout_height="match_parent"
        android:background="#000000"
        android:visibility="gone" />

    <ProgressBar
        android:id="@+id/progressBar"
        style="?android:attr/progressBarStyleHorizontal"
        android:layout_width="match_parent"
        android:layout_height="4dp"
        android:layout_alignParentTop="true"
        android:visibility="gone" />

    <!-- Android TV Virtual Mouse Pointer Overlay -->
    <FrameLayout
        android:id="@+id/tvMouseContainer"
        android:layout_width="48dp"
        android:layout_height="48dp"
        android:clickable="false"
        android:focusable="false"
        android:visibility="gone"
        android:elevation="100dp"
        android:importantForAccessibility="no">

        <View
            android:id="@+id/tvMouseClickRing"
            android:layout_width="16dp"
            android:layout_height="16dp"
            android:layout_gravity="top|start"
            android:layout_marginStart="1dp"
            android:layout_marginTop="1dp"
            android:background="@drawable/tv_mouse_click_ring"
            android:visibility="gone" />

        <ImageView
            android:id="@+id/tvMouseCursor"
            android:layout_width="32dp"
            android:layout_height="32dp"
            android:src="@drawable/ic_tv_mouse_cursor" />
    </FrameLayout>

</RelativeLayout>""", encoding="utf-8")

    @staticmethod
    def _generate_gradle_files(
        project_path: Path,
        app_path: Path,
        package_name: str,
        version_code: int,
        version_name: str
    ):
        (project_path / "build.gradle").write_text("""buildscript {
    repositories {
        google()
        mavenCentral()
    }
    dependencies {
        classpath 'com.android.tools.build:gradle:8.2.2'
    }
}

allprojects {
    repositories {
        google()
        mavenCentral()
    }
}

task clean(type: Delete) {
    delete rootProject.buildDir
}
""", encoding="utf-8")

        (project_path / "settings.gradle").write_text("""include ':app'
rootProject.name = "Web2APKProject"
""", encoding="utf-8")

        (project_path / "gradle.properties").write_text("""org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
android.useAndroidX=true
android.enableJetifier=true
""", encoding="utf-8")

        (app_path / "build.gradle").write_text(f"""plugins {{
    id 'com.android.application'
}}

android {{
    namespace '{package_name}'
    compileSdk 34

    defaultConfig {{
        applicationId "{package_name}"
        minSdk 21
        targetSdk 34
        versionCode {version_code}
        versionName "{version_name}"
    }}

    buildTypes {{
        release {{
            minifyEnabled false
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }}
        debug {{
            debuggable true
        }}
    }}

    compileOptions {{
        sourceCompatibility JavaVersion.VERSION_17
        targetCompatibility JavaVersion.VERSION_17
    }}
}}

dependencies {{
    implementation 'androidx.appcompat:appcompat:1.6.1'
    implementation 'androidx.webkit:webkit:1.10.0'
}}
""", encoding="utf-8")

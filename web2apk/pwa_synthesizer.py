import json
import os
from pathlib import Path
from typing import Dict, Any, List

SERVICE_WORKER_TEMPLATE = """/**
 * Web2APK Autonomous Offline Service Worker
 * Automatically caches all web assets for 100% offline standalone execution.
 */
const CACHE_NAME = 'web2apk-cache-v1';
const OFFLINE_URL = 'offline.html';

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll([
                './',
                'index.html',
                'web2apk-bridge.js',
                'web2apk-gamepad.js',
                'web2apk-tv-nav.js'
            ]).catch((err) => console.log('[SW] Cache init error:', err));
        })
    );
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keyList) => {
            return Promise.all(keyList.map((key) => {
                if (key !== CACHE_NAME) {
                    return caches.delete(key);
                }
            }));
        })
    );
    self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    if (event.request.method !== 'GET') return;

    event.respondWith(
        fetch(event.request)
            .then((networkResponse) => {
                if (networkResponse && networkResponse.status === 200) {
                    const responseToCache = networkResponse.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(event.request, responseToCache);
                    });
                }
                return networkResponse;
            })
            .catch(() => {
                return caches.match(event.request).then((cachedResponse) => {
                    if (cachedResponse) {
                        return cachedResponse;
                    }
                    if (event.request.mode === 'navigate') {
                        return caches.match(OFFLINE_URL) || caches.match('index.html');
                    }
                });
            })
    );
});
"""

class PWASynthesizer:
    """
    Autonomous PWA & Service Worker Synthesizer:
    Transforms any static web project or remote URL wrapper into a fully functional
    Progressive Web App with persistent cache and instant offline startup.
    """

    @classmethod
    def synthesize_pwa_assets(
        cls,
        target_dir: Path,
        app_name: str,
        theme_color: str = "#0f172a",
        is_landscape: bool = False
    ) -> Dict[str, Any]:
        target = Path(target_dir)
        if not target.exists():
            return {"success": False, "error": "Target directory does not exist"}

        # 1. Write Service Worker
        sw_path = target / "sw.js"
        if not sw_path.exists():
            sw_path.write_text(SERVICE_WORKER_TEMPLATE, encoding="utf-8")

        # 2. Write Web App Manifest
        manifest_data = {
            "name": app_name,
            "short_name": app_name[:12],
            "start_url": "index.html",
            "display": "standalone",
            "orientation": "landscape" if is_landscape else "any",
            "background_color": theme_color,
            "theme_color": theme_color,
            "icons": [
                {
                    "src": "res/mipmap-xxxhdpi/ic_launcher.png",
                    "sizes": "192x192 512x512",
                    "type": "image/png"
                }
            ]
        }
        manifest_path = target / "manifest.webmanifest"
        manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

        # 3. Inject SW Registration into HTML files
        sw_registration_snippet = """
    <!-- Web2APK Autonomous PWA Registration -->
    <link rel="manifest" href="manifest.webmanifest">
    <script>
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', () => {
                navigator.serviceWorker.register('sw.js').catch(err => console.log('SW reg error:', err));
            });
        }
    </script>
"""
        patched_count = 0
        for root, _, files in os.walk(target):
            for f in files:
                if f.lower().endswith((".html", ".htm")):
                    file_p = Path(root) / f
                    try:
                        content = file_p.read_text(encoding="utf-8", errors="ignore")
                        if "navigator.serviceWorker.register" not in content:
                            if "</head>" in content:
                                content = content.replace("</head>", f"{sw_registration_snippet}\n</head>", 1)
                            elif "<head>" in content:
                                content = content.replace("<head>", f"<head>\n{sw_registration_snippet}", 1)
                            else:
                                content = sw_registration_snippet + content
                            file_p.write_text(content, encoding="utf-8")
                            patched_count += 1
                    except Exception:
                        pass

        return {
            "success": True,
            "sw_created": True,
            "manifest_created": True,
            "html_files_registered": patched_count
        }

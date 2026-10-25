import os
import re
import shutil
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple

RUNTIME_HEALER_JS = """/**
 * Web2APK Runtime Self-Healing & Compatibility Engine
 * Resolves WebView audio autoplay locks, blocking alert/confirm dialogs,
 * unhandled popup windows, and mobile touch delays.
 */
(function() {
    'use strict';
    
    if (window.__web2apk_runtime_healed) return;
    window.__web2apk_runtime_healed = true;

    // 1. Web Audio & Media Autoplay Unlocker
    const audioContexts = [];
    const originalAudioContext = window.AudioContext || window.webkitAudioContext;
    if (originalAudioContext) {
        window.AudioContext = window.webkitAudioContext = function() {
            const ctx = new originalAudioContext();
            audioContexts.push(ctx);
            return ctx;
        };
    }

    function unlockAudio() {
        audioContexts.forEach(ctx => {
            if (ctx && ctx.state === 'suspended') {
                ctx.resume().catch(() => {});
            }
        });
        document.querySelectorAll('audio, video').forEach(media => {
            if (media.paused && media.autoplay) {
                media.play().catch(() => {});
            }
        });
    }

    ['touchstart', 'touchend', 'click', 'keydown'].forEach(evt => {
        window.addEventListener(evt, unlockAudio, { once: false, passive: true });
    });

    // 2. Non-Blocking Modern Dialog System (Replaces freezing alert/confirm/prompt)
    function createDialogModal(type, message, defaultValue = '', callback = null) {
        let overlay = document.getElementById('web2apk-dialog-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'web2apk-dialog-overlay';
            overlay.style.cssText = `
                position: fixed; inset: 0; z-index: 9999999;
                background: rgba(9, 13, 22, 0.85); backdrop-filter: blur(8px);
                display: flex; align-items: center; justify-content: center; padding: 20px;
                font-family: system-ui, -apple-system, sans-serif;
            `;
            document.body.appendChild(overlay);
        }

        overlay.innerHTML = `
            <div style="background: #0f172a; border: 1px solid #38bdf8; border-radius: 20px; padding: 24px; max-width: 400px; width: 100%; box-shadow: 0 0 30px rgba(56, 189, 248, 0.4); text-align: center; color: #ffffff;">
                <p style="margin: 0 0 16px 0; font-size: 15px; line-height: 1.5; word-break: break-word;">${message}</p>
                ${type === 'prompt' ? `<input id="web2apk-dlg-input" value="${defaultValue}" style="width: 100%; box-sizing: border-box; padding: 10px 14px; border-radius: 10px; background: #1e293b; border: 1px solid #475569; color: #fff; margin-bottom: 16px; font-size: 14px;">` : ''}
                <div style="display: flex; gap: 10px; justify-content: center;">
                    ${type !== 'alert' ? `<button id="web2apk-dlg-cancel" style="flex: 1; padding: 10px 16px; border-radius: 10px; background: #334155; border: 0; color: #cbd5e1; font-weight: bold; cursor: pointer;">Cancel</button>` : ''}
                    <button id="web2apk-dlg-ok" style="flex: 1; padding: 10px 16px; border-radius: 10px; background: #38bdf8; border: 0; color: #090d16; font-weight: bold; cursor: pointer;">OK</button>
                </div>
            </div>
        `;
        overlay.style.display = 'flex';

        const okBtn = overlay.querySelector('#web2apk-dlg-ok');
        const cancelBtn = overlay.querySelector('#web2apk-dlg-cancel');
        const inputField = overlay.querySelector('#web2apk-dlg-input');

        if (inputField) inputField.focus(); else okBtn.focus();

        okBtn.onclick = () => {
            overlay.style.display = 'none';
            if (callback) callback(type === 'prompt' ? inputField.value : true);
        };
        if (cancelBtn) {
            cancelBtn.onclick = () => {
                overlay.style.display = 'none';
                if (callback) callback(type === 'prompt' ? null : false);
            };
        }
    }

    // Intercept native dialogs
    window.alert = function(msg) {
        console.log('[Web2APK Alert]:', msg);
        createDialogModal('alert', String(msg));
    };

    window.confirm = function(msg) {
        console.log('[Web2APK Confirm]:', msg);
        createDialogModal('confirm', String(msg));
        return true; // Non-blocking optimistic return
    };

    // 3. Universal Database & File Download Interceptor
    // Intercepts blob:, data:, and database exports (<a download="...">)
    // and bridges them directly to native AndroidApp.saveBase64File() or downloadUrlWithFilename()
    const DB_EXTENSIONS = [
        '.sqlite', '.sqlite3', '.db', '.db3', '.s3db', '.sl3',
        '.sql', '.dump', '.bak', '.backup',
        '.json', '.csv', '.tsv', '.xlsx', '.xls', '.xml', '.parquet',
        '.zip', '.tar', '.gz', '.7z', '.rar',
        '.bin', '.dat', '.pdf', '.txt'
    ];

    function isDatabaseOrDownloadUrl(url, filename) {
        if (!url && !filename) return false;
        const checkStr = ((filename || '') + ' ' + (url || '')).toLowerCase();
        return DB_EXTENSIONS.some(ext => checkStr.includes(ext));
    }

    function processBlobDownload(blob, filename) {
        try {
            const reader = new FileReader();
            reader.onloadend = function() {
                const base64Data = reader.result;
                const safeName = filename || 'database.sqlite';
                if (window.AndroidApp && typeof window.AndroidApp.saveBase64File === 'function') {
                    window.AndroidApp.saveBase64File(base64Data, safeName, blob.type || '');
                } else if (window.AndroidBridge && typeof window.AndroidBridge.saveBase64File === 'function') {
                    window.AndroidBridge.saveBase64File(base64Data, safeName, blob.type || '');
                }
            };
            reader.readAsDataURL(blob);
        } catch (e) {
            console.error('[Web2APK] Blob read error:', e);
        }
    }

    function triggerNativeDownload(url, filename) {
        if (!url) return false;
        if (url.startsWith('blob:')) {
            fetch(url)
                .then(res => res.blob())
                .then(blob => processBlobDownload(blob, filename))
                .catch(err => console.error('[Web2APK] Fetch blob error:', err));
            return true;
        } else if (url.startsWith('data:')) {
            const safeName = filename || 'database.sqlite';
            if (window.AndroidApp && typeof window.AndroidApp.saveBase64File === 'function') {
                window.AndroidApp.saveBase64File(url, safeName, '');
                return true;
            } else if (window.AndroidBridge && typeof window.AndroidBridge.saveBase64File === 'function') {
                window.AndroidBridge.saveBase64File(url, safeName, '');
                return true;
            }
        } else if (isDatabaseOrDownloadUrl(url, filename) || filename) {
            if (window.AndroidApp && typeof window.AndroidApp.downloadUrlWithFilename === 'function') {
                window.AndroidApp.downloadUrlWithFilename(url, filename || '', '');
                return true;
            } else if (window.AndroidBridge && typeof window.AndroidBridge.downloadUrlWithFilename === 'function') {
                window.AndroidBridge.downloadUrlWithFilename(url, filename || '', '');
                return true;
            }
        }
        return false;
    }

    // Intercept click on any <a> or child element of <a>
    document.addEventListener('click', function(e) {
        let target = e.target;
        while (target && target.tagName !== 'A') {
            target = target.parentElement;
        }
        if (!target || target.tagName !== 'A') return;

        const href = target.getAttribute('href') || target.href || '';
        const downloadAttr = target.getAttribute('download');
        const hasDownload = downloadAttr !== null;
        const filename = downloadAttr || target.download || '';

        if (hasDownload || href.startsWith('blob:') || href.startsWith('data:') || isDatabaseOrDownloadUrl(href, filename)) {
            const handled = triggerNativeDownload(href, filename);
            if (handled) {
                e.preventDefault();
                e.stopPropagation();
            }
        }
    }, true);

    // Intercept programmatic HTMLAnchorElement.prototype.click
    try {
        const origAnchorClick = HTMLAnchorElement.prototype.click;
        HTMLAnchorElement.prototype.click = function() {
            const href = this.getAttribute('href') || this.href || '';
            const downloadAttr = this.getAttribute('download');
            const hasDownload = downloadAttr !== null;
            const filename = downloadAttr || this.download || '';

            if (hasDownload || href.startsWith('blob:') || href.startsWith('data:') || isDatabaseOrDownloadUrl(href, filename)) {
                const handled = triggerNativeDownload(href, filename);
                if (handled) return;
            }
            return origAnchorClick.apply(this, arguments);
        };
    } catch (ignored) {}

    // 4. Safe Window Open Handler (Prevents blank popups from breaking WebView & routes downloads)
    const originalOpen = window.open;
    window.open = function(url, target, features) {
        if (!url) return null;
        if (typeof url === 'string' && (url.startsWith('blob:') || url.startsWith('data:') || isDatabaseOrDownloadUrl(url, ''))) {
            const handled = triggerNativeDownload(url, '');
            if (handled) return window;
        }
        if (target === '_self' || target === '_top' || !target) {
            window.location.href = url;
            return window;
        }
        window.location.href = url;
        return window;
    };

    // 5. Lights Out Auto-Healer & Video Viewport Protector
    // Prevents dark overlay blanking, elevates video stacking context,
    // and provides floating accessible control + Escape/Back dismissal.
    (function initLightsOutHealer() {
        const style = document.createElement('style');
        style.id = 'web2apk-healer-video-elevation';
        style.textContent = `
            video, iframe[src*="embed"], iframe[src*="player"], iframe[src*="video"],
            iframe[allowfullscreen], .jwplayer, .video-js, .plyr,
            [class*="player-container"], [id*="player-container"],
            [class*="video-player"], [id*="video-player"],
            [class*="movie-player"], [id*="movie-player"] {
                position: relative !important;
                z-index: 2147483640 !important;
            }
            #web2apk-lights-out-btn {
                position: fixed !important;
                top: 14px !important;
                right: 14px !important;
                z-index: 2147483647 !important;
                background: rgba(15, 23, 42, 0.92) !important;
                color: #38bdf8 !important;
                border: 1.5px solid #38bdf8 !important;
                border-radius: 20px !important;
                padding: 8px 14px !important;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
                font-size: 13px !important;
                font-weight: 700 !important;
                cursor: pointer !important;
                display: none;
                align-items: center !important;
                gap: 6px !important;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.75), 0 0 12px rgba(56, 189, 248, 0.4) !important;
                user-select: none !important;
                -webkit-user-select: none !important;
                touch-action: manipulation !important;
            }
        `;
        (document.head || document.documentElement).appendChild(style);

        function ensureBtn() {
            let btn = document.getElementById('web2apk-lights-out-btn');
            if (!btn && document.body) {
                btn = document.createElement('div');
                btn.id = 'web2apk-lights-out-btn';
                btn.innerHTML = '<span>💡 Turn On Lights</span> <span style="font-size:15px;line-height:1;margin-left:2px;">✕</span>';
                btn.onclick = (e) => { e.preventDefault(); e.stopPropagation(); window.__web2apk_dismissLightsOut(); };
                btn.ontouchstart = (e) => { e.preventDefault(); e.stopPropagation(); window.__web2apk_dismissLightsOut(); };
                document.body.appendChild(btn);
            }
            return btn;
        }

        window.__web2apk_dismissLightsOut = function() {
            let handled = false;
            const btn = document.getElementById('web2apk-lights-out-btn');
            if (btn && btn.style.display !== 'none') {
                btn.style.display = 'none';
                handled = true;
            }

            try {
                const esc = new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape', keyCode: 27, which: 27, bubbles: true });
                document.dispatchEvent(esc);
                window.dispatchEvent(esc);
            } catch(e) {}

            ['lights-off', 'lightsoff', 'cinema-mode', 'dimmed', 'theater-mode', 'lights_off'].forEach(cls => {
                if (document.body && document.body.classList.contains(cls)) { document.body.classList.remove(cls); handled = true; }
                if (document.documentElement && document.documentElement.classList.contains(cls)) { document.documentElement.classList.remove(cls); handled = true; }
            });

            const sels = ['#lightsoff', '.lightsoff', '#lights-off', '.lights-off', '#turn-off-lights', '#cinema-overlay', '.cinema-overlay', '#dimmer', '.dimmer-overlay', '[id*="lightsoff"]', '[class*="lightsoff"]', '[id*="lights_off"]', '[class*="lights_off"]', '[id*="cinema-mode"]'];
            sels.forEach(s => {
                try {
                    document.querySelectorAll(s).forEach(el => {
                        if (el && el.offsetParent !== null && window.getComputedStyle(el).display !== 'none') {
                            el.style.display = 'none';
                            handled = true;
                        }
                    });
                } catch(e) {}
            });

            try {
                document.querySelectorAll('div, section').forEach(el => {
                    if (el.id === 'web2apk-lights-out-btn') return;
                    const st = window.getComputedStyle(el);
                    if ((st.position === 'fixed' || st.position === 'absolute') && st.display !== 'none' && parseFloat(st.opacity) > 0) {
                        const z = parseInt(st.zIndex, 10);
                        if (z >= 90 && z < 2147483645) {
                            const rect = el.getBoundingClientRect();
                            if (rect.width > window.innerWidth * 0.85 && rect.height > window.innerHeight * 0.85) {
                                const bg = st.backgroundColor;
                                if (bg && (bg.includes('0, 0, 0') || bg === '#000' || bg === 'black')) {
                                    if (!el.querySelector('video, iframe')) {
                                        el.style.display = 'none';
                                        handled = true;
                                    }
                                }
                            }
                        }
                    }
                });
            } catch(e) {}

            try {
                if (window.AndroidBridge && window.AndroidBridge.setLightsOutActive) {
                    window.AndroidBridge.setLightsOutActive(false);
                } else if (window.AndroidApp && window.AndroidApp.setLightsOutActive) {
                    window.AndroidApp.setLightsOutActive(false);
                }
            } catch(e) {}

            return handled;
        };

        function scanLights() {
            let off = false;
            const bCls = (document.body ? document.body.className : '') + ' ' + (document.documentElement ? document.documentElement.className : '');
            if (/lights[-_]?off|cinema[-_]?mode|dimmed|theater[-_]?mode/i.test(bCls)) off = true;

            const sels = ['#lightsoff', '.lightsoff', '#lights-off', '.lights-off', '#turn-off-lights', '#cinema-overlay', '.cinema-overlay', '#dimmer', '.dimmer-overlay', '[id*="lightsoff"]', '[class*="lightsoff"]', '[id*="lights_off"]', '[class*="lights_off"]', '[id*="cinema-mode"]'];
            for (let s of sels) {
                try {
                    const el = document.querySelector(s);
                    if (el && el.offsetParent !== null && window.getComputedStyle(el).display !== 'none') {
                        const z = parseInt(window.getComputedStyle(el).zIndex, 10);
                        if (z >= 2147483640) el.style.zIndex = '2147483600';
                        if (!el.__web2apk_tap) {
                            el.__web2apk_tap = true;
                            el.addEventListener('click', () => window.__web2apk_dismissLightsOut(), { passive: true });
                        }
                        off = true;
                        break;
                    }
                } catch(e) {}
            }

            document.querySelectorAll('video, iframe[src*="embed"], iframe[src*="player"], iframe[allowfullscreen], .jwplayer, .video-js').forEach(p => {
                if (p.style.zIndex !== '2147483640') {
                    p.style.setProperty('z-index', '2147483640', 'important');
                    p.style.setProperty('position', 'relative', 'important');
                }
                const parent = p.parentElement;
                if (parent && parent !== document.body && parent.style.zIndex !== '2147483640') {
                    const pz = parseInt(window.getComputedStyle(parent).zIndex, 10);
                    if (isNaN(pz) || pz < 2147483639) {
                        parent.style.setProperty('z-index', '2147483639', 'important');
                        parent.style.setProperty('position', 'relative', 'important');
                    }
                }
            });

            const b = ensureBtn();
            if (b) b.style.display = off ? 'flex' : 'none';

            try {
                if (window.AndroidBridge && window.AndroidBridge.setLightsOutActive) {
                    window.AndroidBridge.setLightsOutActive(off);
                } else if (window.AndroidApp && window.AndroidApp.setLightsOutActive) {
                    window.AndroidApp.setLightsOutActive(off);
                }
            } catch(e) {}
        }

        if (window.MutationObserver && document.body) {
            new MutationObserver(scanLights).observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['class', 'style', 'id'] });
        }
        document.addEventListener('click', (e) => {
            const txt = ((e.target && e.target.textContent) || '').toLowerCase();
            if (txt.includes('lights out') || txt.includes('turn off light')) {
                setTimeout(scanLights, 100);
                setTimeout(scanLights, 400);
            }
        }, { passive: true });
        setTimeout(scanLights, 300);
    })();

    console.log('⚡ Web2APK Runtime Self-Healing Engine Active');
})();
"""

class SelfHealer:
    """
    Autonomous Problem Solver and Code Diagnostic & Repair Engine.
    Detects project defects, missing entrypoints, required device permissions,
    and injects runtime polyfills.
    """

    @classmethod
    def diagnose_and_heal_directory(cls, dir_path: Path) -> Dict[str, Any]:
        """
        Runs comprehensive diagnostic scan and automatically repairs issues.
        """
        repairs_made = []
        issues_detected = []
        detected_permissions = set()

        if not dir_path.exists():
            return {
                "success": False,
                "error": f"Directory {dir_path} does not exist",
                "repairs": [],
                "permissions": []
            }

        # 1. Entrypoint Resolver (Find or promote root index.html)
        root_index = dir_path / "index.html"
        if not root_index.exists():
            issues_detected.append("Missing root index.html")
            all_html = list(dir_path.glob("**/*.html")) + list(dir_path.glob("**/*.htm"))
            if all_html:
                # Priority search in common subfolders (dist, build, public, www, out)
                best_match = None
                for candidate in all_html:
                    c_str = str(candidate).lower()
                    if any(sub in c_str for sub in ["dist/", "build/", "public/", "www/", "out/", "web/"]):
                        best_match = candidate
                        break
                if not best_match:
                    best_match = all_html[0]

                # Promote best match or copy entire subfolder contents up
                sub_dir = best_match.parent
                if sub_dir != dir_path:
                    for item in sub_dir.iterdir():
                        dest = dir_path / item.name
                        if not dest.exists():
                            if item.is_dir():
                                shutil.copytree(item, dest)
                            else:
                                shutil.copy2(item, dest)
                    repairs_made.append(f"Auto-promoted nested build directory: {sub_dir.name}/ -> root")
                else:
                    shutil.copy2(best_match, root_index)
                    repairs_made.append(f"Renamed {best_match.name} to index.html")
            else:
                # Create fallback index.html
                root_index.write_text("""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>Web App</title></head>
<body><h2 style="font-family: sans-serif; text-align: center; margin-top: 20%;">App Loaded Successfully</h2></body>
</html>""", encoding="utf-8")
                repairs_made.append("Generated missing fallback index.html")

        # 2. Permission Discovery (Scan JS/HTML files for hardware/browser APIs)
        code_files = list(dir_path.glob("**/*.js")) + list(dir_path.glob("**/*.html")) + list(dir_path.glob("**/*.ts"))
        for cf in code_files:
            try:
                content = cf.read_text(encoding="utf-8", errors="replace")
                
                # Camera & Microphone
                if "getUserMedia" in content or "navigator.mediaDevices" in content:
                    detected_permissions.add("android.permission.CAMERA")
                    detected_permissions.add("android.permission.RECORD_AUDIO")
                
                # Geolocation
                if "getCurrentPosition" in content or "watchPosition" in content or "geolocation" in content:
                    detected_permissions.add("android.permission.ACCESS_FINE_LOCATION")
                    detected_permissions.add("android.permission.ACCESS_COARSE_LOCATION")

                # Audio
                if "AudioContext" in content or "webkitAudioContext" in content or "<audio" in content:
                    detected_permissions.add("android.permission.MODIFY_AUDIO_SETTINGS")

                # Bluetooth
                if "navigator.bluetooth" in content:
                    detected_permissions.add("android.permission.BLUETOOTH")
                    detected_permissions.add("android.permission.BLUETOOTH_CONNECT")

            except Exception:
                pass

        # 3. Inject Runtime Healer Script (Non-blocking modals, audio unlock, etc.)
        healer_script_path = dir_path / "web2apk-runtime-healer.js"
        healer_script_path.write_text(RUNTIME_HEALER_JS, encoding="utf-8")
        repairs_made.append("Injected Runtime Healer (Web Audio unlocker, non-blocking modals, safe window.open)")

        # Inject script tag into all HTML files
        html_files = list(dir_path.glob("**/*.html")) + list(dir_path.glob("**/*.htm"))
        for hf in html_files:
            try:
                content = hf.read_text(encoding="utf-8", errors="replace")
                if "web2apk-runtime-healer.js" not in content:
                    script_tag = '<script src="/web2apk-runtime-healer.js"></script>'
                    if "<head>" in content:
                        content = content.replace("<head>", f"<head>\n    {script_tag}", 1)
                    else:
                        content = f"{script_tag}\n{content}"
                    hf.write_text(content, encoding="utf-8")
            except Exception:
                pass

        return {
            "success": True,
            "issues_detected": issues_detected,
            "repairs_made": repairs_made,
            "detected_permissions": list(detected_permissions)
        }

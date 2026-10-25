import os
import re
import shutil
from pathlib import Path
from typing import Dict, Any, List

from .security.hardener import SecurityHardener

TV_DPAD_NAV_JS = """/**
 * Web2APK TV D-Pad & Gamepad Spatial Navigation Engine
 * Enables remote control (DPAD) and Gamepad navigation on Android TV & Smart Screens.
 */
(function() {
    'use strict';
    
    if (window.__web2apk_tv_nav_loaded) return;
    window.__web2apk_tv_nav_loaded = true;
    
    // Inject TV Focus Styling
    const style = document.createElement('style');
    style.id = 'web2apk-tv-styles';
    style.textContent = `
        .web2apk-tv-focused {
            outline: 4px solid #38bdf8 !important;
            outline-offset: 3px !important;
            box-shadow: 0 0 25px rgba(56, 189, 248, 0.9), 0 0 10px rgba(56, 189, 248, 0.6) !important;
            transform: scale(1.04) !important;
            transition: transform 0.15s ease, outline 0.15s ease, box-shadow 0.15s ease !important;
            z-index: 999999 !important;
        }
        
        body.web2apk-tv-mode {
            user-select: none;
            -webkit-user-select: none;
            cursor: default;
        }
    `;
    document.head.appendChild(style);
    document.body.classList.add('web2apk-tv-mode');

    let currentFocus = null;

    function getFocusableElements() {
        const selector = [
            'a[href]',
            'button:not([disabled])',
            'input:not([disabled]):not([type="hidden"])',
            'select:not([disabled])',
            'textarea:not([disabled])',
            '[tabindex]:not([tabindex="-1"])',
            '[role="button"]',
            '[role="link"]',
            '[role="tab"]',
            '[role="menuitem"]',
            '[onclick]',
            'video[controls]',
            'audio[controls]'
        ].join(', ');

        const all = Array.from(document.querySelectorAll(selector));
        return all.filter(el => {
            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            return (
                rect.width > 0 &&
                rect.height > 0 &&
                style.visibility !== 'hidden' &&
                style.display !== 'none' &&
                style.opacity !== '0'
            );
        });
    }

    function setFocus(el) {
        if (!el) return;
        if (currentFocus) {
            currentFocus.classList.remove('web2apk-tv-focused');
        }
        currentFocus = el;
        currentFocus.classList.add('web2apk-tv-focused');
        currentFocus.focus();
        currentFocus.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'nearest' });
    }

    function initSpatialNavigation() {
        const focusables = getFocusableElements();
        if (focusables.length > 0 && !currentFocus) {
            setFocus(focusables[0]);
        }

        window.addEventListener('keydown', function(e) {
            const focusables = getFocusableElements();
            if (focusables.length === 0) return;

            if (!currentFocus || !document.body.contains(currentFocus)) {
                setFocus(focusables[0]);
                return;
            }

            const curIdx = focusables.indexOf(currentFocus);
            const curRect = currentFocus.getBoundingClientRect();

            let nextEl = null;

            switch (e.keyCode) {
                case 38: // UP
                    nextEl = findClosestElement(curRect, focusables, 'up');
                    break;
                case 40: // DOWN
                    nextEl = findClosestElement(curRect, focusables, 'down');
                    break;
                case 37: // LEFT
                    nextEl = findClosestElement(curRect, focusables, 'left');
                    break;
                case 39: // RIGHT
                    nextEl = findClosestElement(curRect, focusables, 'right');
                    break;
                case 13: // ENTER / DPAD_CENTER
                    if (currentFocus) {
                        currentFocus.click();
                        e.preventDefault();
                    }
                    return;
                case 27: // BACK / ESCAPE
                    window.history.back();
                    e.preventDefault();
                    return;
                default:
                    return;
            }

            if (nextEl) {
                setFocus(nextEl);
                e.preventDefault();
            } else if (e.keyCode === 40 && curIdx < focusables.length - 1) {
                setFocus(focusables[curIdx + 1]);
                e.preventDefault();
            } else if (e.keyCode === 38 && curIdx > 0) {
                setFocus(focusables[curIdx - 1]);
                e.preventDefault();
            }
        });
    }

    function findClosestElement(curRect, candidates, direction) {
        let closest = null;
        let minDistance = Infinity;

        const curCenter = {
            x: curRect.left + curRect.width / 2,
            y: curRect.top + curRect.height / 2
        };

        for (const el of candidates) {
            if (el === currentFocus) continue;

            const rect = el.getBoundingClientRect();
            const center = {
                x: rect.left + rect.width / 2,
                y: rect.top + rect.height / 2
            };

            let isValid = false;

            if (direction === 'up' && center.y < curCenter.y - 5) isValid = true;
            if (direction === 'down' && center.y > curCenter.y + 5) isValid = true;
            if (direction === 'left' && center.x < curCenter.x - 5) isValid = true;
            if (direction === 'right' && center.x > curCenter.x + 5) isValid = true;

            if (isValid) {
                const dx = center.x - curCenter.x;
                const dy = center.y - curCenter.y;
                let dist = Math.sqrt(dx * dx + dy * dy);

                if (direction === 'up' || direction === 'down') {
                    dist += Math.abs(dx) * 1.5;
                } else {
                    dist += Math.abs(dy) * 1.5;
                }

                if (dist < minDistance) {
                    minDistance = dist;
                    closest = el;
                }
            }
        }

        return closest;
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSpatialNavigation);
    } else {
        initSpatialNavigation();
    }
})();
"""

class CodePatcher:
    """
    Code Patcher & Security Hardener:
    - Injects Content-Security-Policy (CSP) and Cyber Defense Runtime Shield
    - Injects Viewport metadata, Notch Safe-Area CSS, and Offline Resilience
    - Injects Android TV Remote D-Pad Navigation and Bluetooth Gamepad Mapper
    - Injects Native Hardware JavaScript Bridge (window.Web2APK)
    """

    @classmethod
    def patch_directory(
        cls,
        target_dir: Path,
        app_title: str = "",
        enable_tv_nav: bool = True,
        enable_notch_css: bool = True,
        enable_security_shield: bool = True
    ) -> Dict[str, Any]:
        target = Path(target_dir)
        stats = {
            "html_files_found": 0,
            "patched_files": 0,
            "viewports_added": 0,
            "safe_areas_added": 0,
            "tv_nav_injected": 0,
            "bridge_injected": 0,
            "security_hardened": 0,
            "iframes_patched": 0
        }

        if not target.exists():
            return {"success": False, "error": f"Directory not found: {target_dir}", "stats": stats}

        # 1. Copy Core Native Assets into workspace
        assets_src_dir = Path(__file__).parent / "assets"
        
        # Copy web2apk-tv-nav.js
        tv_nav_path = target / "web2apk-tv-nav.js"
        if not tv_nav_path.exists() and enable_tv_nav:
            tv_nav_path.write_text(TV_DPAD_NAV_JS, encoding="utf-8")
        
        # Copy web2apk-bridge.js
        bridge_src = assets_src_dir / "web2apk-bridge.js"
        if bridge_src.exists():
            shutil.copy2(bridge_src, target / "web2apk-bridge.js")

        # Copy web2apk-gamepad.js
        gamepad_src = assets_src_dir / "web2apk-gamepad.js"
        if gamepad_src.exists():
            shutil.copy2(gamepad_src, target / "web2apk-gamepad.js")

        # 2. Discover and Patch HTML Files
        html_files = []
        for root, _, files in os.walk(target):
            for f in files:
                if f.lower().endswith(('.html', '.htm')):
                    html_files.append(Path(root) / f)

        stats["html_files_found"] = len(html_files)

        for html_file in html_files:
            try:
                content = html_file.read_text(encoding='utf-8', errors='ignore')
                modified = False

                # Relative path calculation
                try:
                    rel_to_root = html_file.parent.relative_to(target)
                    nesting_depth = len(rel_to_root.parts)
                    prefix = "../" * nesting_depth
                except ValueError:
                    prefix = ""

                tv_nav_rel_path = f"{prefix}web2apk-tv-nav.js"

                # 1. UTF-8 Charset
                if '<meta charset' not in content.lower():
                    if '<head>' in content:
                        content = content.replace('<head>', '<head>\n    <meta charset="UTF-8">', 1)
                        modified = True

                # 2. Viewport optimization
                viewport_tag = '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">'
                if '<meta name="viewport"' in content.lower() or "<meta name='viewport'" in content.lower():
                    content = re.sub(
                        r'<meta\s+name=["\']viewport["\'][^>]*>',
                        viewport_tag,
                        content,
                        flags=re.IGNORECASE
                    )
                    modified = True
                else:
                    if '<head>' in content:
                        content = content.replace('<head>', f'<head>\n    {viewport_tag}', 1)
                        stats["viewports_added"] += 1
                        modified = True

                # 3. Safe-Area notch support CSS
                if enable_notch_css and 'safe-area-inset-top' not in content:
                    safe_area_style = """
    <style id="web2apk-safe-areas">
        :root {
            --sat: env(safe-area-inset-top, 0px);
            --sab: env(safe-area-inset-bottom, 0px);
            --sal: env(safe-area-inset-left, 0px);
            --sar: env(safe-area-inset-right, 0px);
        }
        body {
            padding-top: var(--sat);
            padding-bottom: var(--sab);
            padding-left: var(--sal);
            padding-right: var(--sar);
            margin: 0;
            overflow-x: hidden;
            -webkit-tap-highlight-color: transparent;
        }
    </style>
                    """
                    if '</head>' in content:
                        content = content.replace('</head>', f'{safe_area_style}\n</head>', 1)
                        stats["safe_areas_added"] += 1
                        modified = True

                # 4. Inject Native Bridge & Gamepad scripts
                bridge_tags = f"""
    <!-- Web2APK Native Bridge & Gamepad System -->
    <script src="{prefix}web2apk-bridge.js"></script>
    <script src="{prefix}web2apk-gamepad.js"></script>
"""
                if 'web2apk-bridge.js' not in content:
                    if '</head>' in content:
                        content = content.replace('</head>', f'{bridge_tags}\n</head>', 1)
                    elif '<head>' in content:
                        content = content.replace('<head>', f'<head>\n{bridge_tags}', 1)
                    stats["bridge_injected"] += 1
                    modified = True

                # 5. Inject TV Navigation Script
                if enable_tv_nav and 'web2apk-tv-nav.js' not in content:
                    script_tag = f'<script src="{tv_nav_rel_path}"></script>'
                    if '</body>' in content:
                        content = content.replace('</body>', f'    {script_tag}\n</body>', 1)
                    else:
                        content += f'\n{script_tag}'
                    stats["tv_nav_injected"] += 1
                    modified = True

                # 6. Apply Cyber Defense & Hardening (CSP, Anti-Clickjack, Protocol Shield)
                if enable_security_shield and 'Content-Security-Policy' not in content:
                    content = SecurityHardener.harden_html(content, enforce_csp=True)
                    stats["security_hardened"] += 1
                    modified = True

                # 7. Patch <iframe> tags for Cinema / HTML5 Video Fullscreen & Media Playback
                if '<iframe' in content.lower():
                    def patch_iframe(match):
                        iframe_tag = match.group(0)
                        if not re.search(r'\ballowfullscreen\b', iframe_tag, re.IGNORECASE):
                            iframe_tag = re.sub(r'(<iframe\b)', r'\1 allowfullscreen="true"', iframe_tag, count=1, flags=re.IGNORECASE)
                        allow_match = re.search(r'\ballow=(["\'])(.*?)\1', iframe_tag, re.IGNORECASE)
                        required_perms = ['autoplay', 'fullscreen', 'encrypted-media', 'picture-in-picture']
                        if allow_match:
                            quote = allow_match.group(1)
                            existing_perms = [p.strip() for p in allow_match.group(2).split(';') if p.strip()]
                            for p in required_perms:
                                if p not in existing_perms:
                                    existing_perms.append(p)
                            new_allow_str = f'allow={quote}{"; ".join(existing_perms)}{quote}'
                            iframe_tag = iframe_tag[:allow_match.start()] + new_allow_str + iframe_tag[allow_match.end():]
                        else:
                            iframe_tag = re.sub(r'(<iframe\b)', r'\1 allow="autoplay; fullscreen; encrypted-media; picture-in-picture"', iframe_tag, count=1, flags=re.IGNORECASE)
                        return iframe_tag

                    new_content, count = re.subn(r'<iframe\b[^>]*>', patch_iframe, content, flags=re.IGNORECASE)
                    if count > 0 and new_content != content:
                        content = new_content
                        stats["iframes_patched"] += count
                        modified = True

                # 8. Set title if provided and missing
                if app_title and ('<title>' not in content.lower()):
                    if '<head>' in content:
                        content = content.replace('<head>', f'<head>\n    <title>{app_title}</title>', 1)
                        modified = True

                if modified:
                    html_file.write_text(content, encoding='utf-8')
                    stats["patched_files"] += 1

            except Exception as e:
                print(f"[CodePatcher] Warning: Could not patch {html_file}: {e}")

        return {"success": True, "stats": stats}

CodePatcher.patch_html_directory = CodePatcher.patch_directory

import os
import re
import io
import json
import base64
import shutil
import tempfile
import urllib.parse
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import requests
from PIL import Image

from .security.server_shield import SSRFProtector
from .evolution import EvolutionEngine
from .icon_generator import IconGenerator

CACHE_DIR = Path.home() / ".web2apk" / "inspector_cache"
ICONS_DIR = Path.home() / ".web2apk" / "icons"

class AppInspector:
    """
    Deep Multi-Source Application Inspector.
    Autonomously analyzes Web Folders, ZIP Archives, and Live URLs to extract:
    - High-Resolution Brand Icon / Logo (with Base64 preview)
    - Application Name & Reverse Domain Package ID
    - Theme & Status Bar Colors
    - Optimal Orientation (Sensor, Portrait, Landscape for WebGL/Canvas games)
    - Immersive Fullscreen & Android TV compatibility
    - Runtime System Permissions (Camera, Mic, Location, Storage, Notifications, etc.)
    - Web Framework & Architecture
    """

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8"
    }

    PERMISSION_PATTERNS = {
        "android.permission.CAMERA": [
            r"navigator\.mediaDevices\.getUserMedia",
            r"navigator\.getUserMedia",
            r'video:\s*true',
            r'facingMode',
            r'capture=["\']camera["\']'
        ],
        "android.permission.RECORD_AUDIO": [
            r"navigator\.mediaDevices\.getUserMedia",
            r"navigator\.getUserMedia",
            r'audio:\s*true',
            r'AudioContext',
            r'webkitAudioContext',
            r'MediaRecorder'
        ],
        "android.permission.ACCESS_FINE_LOCATION": [
            r"navigator\.geolocation",
            r"getCurrentPosition",
            r"watchPosition"
        ],
        "android.permission.ACCESS_COARSE_LOCATION": [
            r"navigator\.geolocation"
        ],
        "android.permission.POST_NOTIFICATIONS": [
            r"Notification\.requestPermission",
            r"new\s+Notification",
            r"registration\.showNotification",
            r"PushManager"
        ],
        "android.permission.VIBRATE": [
            r"navigator\.vibrate"
        ],
        "android.permission.BLUETOOTH": [
            r"navigator\.bluetooth",
            r"requestDevice"
        ],
        "android.permission.BLUETOOTH_CONNECT": [
            r"navigator\.bluetooth"
        ],
        "android.permission.READ_EXTERNAL_STORAGE": [
            r'<input[^>]+type=["\']file["\']',
            r'showOpenFilePicker',
            r'FileReader',
            r'indexedDB'
        ],
        "android.permission.WRITE_EXTERNAL_STORAGE": [
            r'showSaveFilePicker',
            r'createObjectURL.*download',
            r'download=["\']'
        ]
    }

    GAME_FRAMEWORK_PATTERNS = [
        r"phaser(?:\.min)?\.js",
        r"three(?:\.min)?\.js",
        r"pixi(?:\.min)?\.js",
        r"babylon(?:\.min)?\.js",
        r"unity.*\.js",
        r"godot.*\.js",
        r"crafty.*\.js",
        r"playcanvas.*\.js",
        r"impact.*\.js",
        r"construct.*\.js",
        r"<canvas[^>]*id=[\"'](?:game|canvas|stage|renderCanvas)[\"']",
        r"<canvas",
        r"createElement\([\"']canvas[\"']\)",
        r"getContext\([\"'](?:2d|webgl|webgl2|experimental-webgl)[\"']\)",
        r"renderCanvas|gameCanvas",
        r"WebGLRenderingContext",
        r"requestAnimationFrame"
    ]

    @classmethod
    def inspect(cls, source: Union[str, Path]) -> Dict[str, Any]:
        """
        Unified inspection entrypoint for URLs, directories, or ZIP files.
        """
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        ICONS_DIR.mkdir(parents=True, exist_ok=True)

        source_str = str(source).strip()
        if source_str.startswith("http://") or source_str.startswith("https://") or ("://" not in source_str and not os.path.exists(source_str) and "." in source_str and not source_str.endswith(".zip") and "/" not in source_str):
            return cls.inspect_url(source_str)

        source_path = Path(source_str).resolve()
        if source_path.is_file() and source_path.suffix.lower() == ".zip":
            return cls.inspect_zip(source_path)
        elif source_path.is_dir():
            return cls.inspect_directory(source_path)
        else:
            if not source_str.startswith("http://") and not source_str.startswith("https://"):
                return cls.inspect_url(f"https://{source_str}")
            return cls.inspect_url(source_str)

    @classmethod
    def inspect_url(cls, url: str) -> Dict[str, Any]:
        """
        Inspects live website URL, extracting full blueprint and branding assets.
        """
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        ICONS_DIR.mkdir(parents=True, exist_ok=True)

        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"https://{url}"

        # SSRF Security Shield Check
        safe, reason = SSRFProtector.is_url_safe(url)
        if not safe:
            raise ValueError(f"[CyberShield] {reason}")

        parsed_url = urllib.parse.urlparse(url)
        domain = parsed_url.netloc
        scheme = parsed_url.scheme
        base_url = f"{scheme}://{domain}"

        clean_domain_name = domain.replace("www.", "").split(".")[0].title()
        reversed_parts = [p for p in reversed(domain.replace("www.", "").split(".")) if p]
        pkg_domain = ".".join(reversed_parts) if len(reversed_parts) >= 2 else f"com.{domain.replace('www.', '')}"
        pkg_domain = re.sub(r'[^a-zA-Z0-9._]', '', pkg_domain.lower())

        blueprint = {
            "source_type": "url",
            "url": url,
            "domain": domain,
            "app_name": clean_domain_name,
            "package_name": pkg_domain if '.' in pkg_domain else f"com.web2apk.{pkg_domain}",
            "version_name": "1.0.0",
            "theme_color": "#0f172a",
            "orientation": "sensor",
            "is_fullscreen": True,
            "is_tv": True,
            "icon_path": None,
            "icon_base64": None,
            "detected_permissions": ["android.permission.INTERNET", "android.permission.ACCESS_NETWORK_STATE", "android.permission.ACCESS_WIFI_STATE"],
            "framework": "Live Web Application",
            "detection_sources": {}
        }

        candidate_icon_urls = []
        html_content = ""

        try:
            resp = requests.get(url, headers=cls.HEADERS, timeout=6, verify=False)
            html_content = resp.text

            # 1. App Title Discovery
            title_match = re.search(r"<title[^>]*>(.*?)</title>", html_content, re.IGNORECASE | re.DOTALL)
            if title_match:
                raw_title = title_match.group(1).strip()
                clean_title = re.split(r"[-|•–—:»]", raw_title)[0].strip()
                if clean_title and len(clean_title) <= 40:
                    blueprint["app_name"] = clean_title
                    clean_slug = re.sub(r'[^a-zA-Z0-9]', '', clean_title.lower())
                    if clean_slug:
                        blueprint["package_name"] = f"com.web2apk.{clean_slug}"
                    blueprint["detection_sources"]["app_name"] = "HTML <title>"

            og_site = re.search(r'<meta\s+(?:property|name)=["\']og:site_name["\']\s+content=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
            if og_site:
                blueprint["app_name"] = og_site.group(1).strip()
                blueprint["detection_sources"]["app_name"] = "OpenGraph og:site_name"

            # 2. Theme Color Discovery
            theme_meta = re.search(r'<meta\s+name=["\']theme-color["\']\s+content=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
            if not theme_meta:
                theme_meta = re.search(r'<meta\s+content=["\']([^"\']+)["\']\s+name=["\']theme-color["\']', html_content, re.IGNORECASE)
            if theme_meta:
                col = theme_meta.group(1).strip()
                if re.match(r"^#(?:[0-9a-fA-F]{3}){1,2}$", col):
                    blueprint["theme_color"] = cls._normalize_hex_color(col)
                    blueprint["detection_sources"]["theme_color"] = "HTML meta theme-color"

            # 3. PWA Manifest Discovery
            manifest_link = re.search(r'<link\s+[^>]*rel=["\']manifest["\'][^>]*href=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
            if manifest_link:
                m_href = manifest_link.group(1)
                m_url = urllib.parse.urljoin(url, m_href)
                m_safe, _ = SSRFProtector.is_url_safe(m_url)
                if m_safe:
                    try:
                        m_resp = requests.get(m_url, headers=cls.HEADERS, timeout=4, verify=False)
                        if m_resp.status_code == 200:
                            m_json = m_resp.json()
                            if "name" in m_json and m_json["name"]:
                                blueprint["app_name"] = m_json["name"].strip()
                                blueprint["detection_sources"]["app_name"] = "PWA Manifest name"
                            elif "short_name" in m_json and m_json["short_name"]:
                                blueprint["app_name"] = m_json["short_name"].strip()
                                blueprint["detection_sources"]["app_name"] = "PWA Manifest short_name"

                            if "theme_color" in m_json and m_json["theme_color"]:
                                blueprint["theme_color"] = cls._normalize_hex_color(m_json["theme_color"])
                                blueprint["detection_sources"]["theme_color"] = "PWA Manifest theme_color"
                            elif "background_color" in m_json and m_json["background_color"]:
                                blueprint["theme_color"] = cls._normalize_hex_color(m_json["background_color"])

                            if "orientation" in m_json:
                                ori = m_json["orientation"].lower()
                                if "landscape" in ori:
                                    blueprint["orientation"] = "landscape"
                                    blueprint["detection_sources"]["orientation"] = "PWA Manifest orientation"
                                elif "portrait" in ori:
                                    blueprint["orientation"] = "portrait"
                                    blueprint["detection_sources"]["orientation"] = "PWA Manifest orientation"

                            if "display" in m_json:
                                disp = m_json["display"].lower()
                                blueprint["is_fullscreen"] = (disp in ["fullscreen", "standalone"])
                                blueprint["detection_sources"]["is_fullscreen"] = f"PWA Manifest display={disp}"

                            icons = m_json.get("icons", [])
                            for ic in reversed(icons):
                                if "src" in ic:
                                    candidate_icon_urls.append(urllib.parse.urljoin(m_url, ic["src"]))
                    except Exception:
                        pass

            # 4. Apple Touch Icons & OpenGraph Images
            apple_icons = re.findall(r'<link\s+[^>]*rel=["\']apple-touch-icon(?:-precomposed)?["\'][^>]*href=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
            for ai in apple_icons:
                candidate_icon_urls.append(urllib.parse.urljoin(url, ai))

            og_image = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
            if og_image:
                candidate_icon_urls.append(urllib.parse.urljoin(url, og_image.group(1)))

            favicons = re.findall(r'<link\s+[^>]*rel=["\'](?:shortcut\s+)?icon["\'][^>]*href=["\']([^"\']+)["\']', html_content, re.IGNORECASE)
            for fi in favicons:
                candidate_icon_urls.append(urllib.parse.urljoin(url, fi))

            # 5. HTML <img> tags with logo / brand in class, id, alt, or src
            html_img_logos = re.findall(r'<img[^>]+(?:class|id|alt|src)=["\'][^"\']*(?:logo|brand|icon)[^"\']*["\'][^>]*>', html_content, re.IGNORECASE)
            for img_tag in html_img_logos:
                src_m = re.search(r'src=["\']([^"\']+)["\']', img_tag)
                if src_m:
                    candidate_icon_urls.append(urllib.parse.urljoin(url, src_m.group(1)))

            # 6. Inline <svg> tags with logo or brand
            inline_svgs = re.findall(r'(<svg[^>]+(?:class|id|aria-label)=["\'][^"\']*(?:logo|brand)[^"\']*["\'][^>]*>.*?</svg>)', html_content, re.IGNORECASE | re.DOTALL)
            for svg_m in inline_svgs[:2]:
                encoded_svg = urllib.parse.quote(svg_m)
                candidate_icon_urls.append(f"data:image/svg+xml;utf8,{encoded_svg}")

            # 7. Common static logo paths on domain
            candidate_icon_urls.append(f"{base_url}/logo.svg")
            candidate_icon_urls.append(f"{base_url}/assets/logo.svg")
            candidate_icon_urls.append(f"{base_url}/favicon.svg")
            candidate_icon_urls.append(f"{base_url}/logo.png")
            candidate_icon_urls.append(f"{base_url}/assets/logo.png")

            # 5. Permission & Game Engines Detection in HTML
            for perm, patterns in cls.PERMISSION_PATTERNS.items():
                for pat in patterns:
                    if re.search(pat, html_content, re.IGNORECASE):
                        if perm not in blueprint["detected_permissions"]:
                            blueprint["detected_permissions"].append(perm)
                        break

            # 6. Canvas / WebGL Game Detection
            for game_pat in cls.GAME_FRAMEWORK_PATTERNS:
                if re.search(game_pat, html_content, re.IGNORECASE):
                    blueprint["orientation"] = "landscape"
                    blueprint["is_fullscreen"] = True
                    blueprint["detection_sources"]["orientation"] = "HTML5 Canvas / Game Engine Detected"
                    blueprint["framework"] = "HTML5 Game / WebGL Canvas"
                    break

        except Exception as e:
            print(f"[AppInspector] URL fetch warning for {url}: {e}")

        # Favicon APIs & domain fallback icons
        candidate_icon_urls.append(f"https://t3.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL&url={urllib.parse.quote(url)}&size=256")
        candidate_icon_urls.append(f"https://www.google.com/s2/favicons?domain={domain}&sz=512")
        candidate_icon_urls.append(f"https://icons.duckduckgo.com/ip3/{domain}.ico")
        candidate_icon_urls.append(f"{base_url}/favicon.ico")

        # Download best icon
        icon_file = cls._download_and_normalize_icon(candidate_icon_urls, domain, blueprint["app_name"])
        if icon_file and icon_file.exists():
            blueprint["icon_path"] = str(icon_file)
            blueprint["icon_base64"] = cls._file_to_base64(icon_file)
            blueprint["detection_sources"]["icon"] = "Extracted High-Res Web Brand Logo"
        else:
            # Fallback generated icon
            fallback_img = IconGenerator._create_fallback_icon(blueprint["app_name"], 512)
            safe_domain = re.sub(r'[^a-zA-Z0-9]', '_', domain)
            fallback_path = ICONS_DIR / f"icon_{safe_domain}.png"
            fallback_img.save(fallback_path, "PNG")
            blueprint["icon_path"] = str(fallback_path)
            blueprint["icon_base64"] = cls._file_to_base64(fallback_path)
            blueprint["detection_sources"]["icon"] = "Algorithmic Squircle Badge"

        return blueprint

    @classmethod
    def inspect_directory(cls, dir_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Deep inspection of a local Web application folder.
        """
        dir_path = Path(dir_path).resolve()
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        ICONS_DIR.mkdir(parents=True, exist_ok=True)

        default_app_name = dir_path.name.replace("-", " ").replace("_", " ").title() or "Web App"
        clean_slug = re.sub(r'[^a-zA-Z0-9]', '', default_app_name.lower()) or "app"

        blueprint = {
            "source_type": "directory",
            "source_path": str(dir_path),
            "app_name": default_app_name,
            "package_name": f"com.web2apk.{clean_slug}",
            "version_name": "1.0.0",
            "theme_color": "#0f172a",
            "orientation": "sensor",
            "is_fullscreen": True,
            "is_tv": True,
            "icon_path": None,
            "icon_base64": None,
            "detected_permissions": ["android.permission.INTERNET", "android.permission.ACCESS_NETWORK_STATE", "android.permission.ACCESS_WIFI_STATE"],
            "framework": EvolutionEngine.identify_framework(dir_path),
            "detection_sources": {}
        }

        # 1. Check package.json
        pkg_json_file = dir_path / "package.json"
        if pkg_json_file.exists():
            try:
                pkg_data = json.loads(pkg_json_file.read_text(encoding="utf-8"))
                if "name" in pkg_data and pkg_data["name"]:
                    raw_pkg_name = pkg_data["name"].replace("@", "").replace("/", " ").replace("-", " ").title()
                    blueprint["app_name"] = raw_pkg_name
                    blueprint["detection_sources"]["app_name"] = "package.json name"
                if "version" in pkg_data and pkg_data["version"]:
                    blueprint["version_name"] = str(pkg_data["version"])
            except Exception:
                pass

        # 2. Check manifest.json / site.webmanifest
        manifest_files = list(dir_path.glob("**/manifest.json")) + list(dir_path.glob("**/*.webmanifest"))
        manifest_icon_candidates = []
        if manifest_files:
            try:
                m_data = json.loads(manifest_files[0].read_text(encoding="utf-8"))
                if "name" in m_data and m_data["name"]:
                    blueprint["app_name"] = m_data["name"].strip()
                    blueprint["detection_sources"]["app_name"] = "manifest.json name"
                elif "short_name" in m_data and m_data["short_name"]:
                    blueprint["app_name"] = m_data["short_name"].strip()
                    blueprint["detection_sources"]["app_name"] = "manifest.json short_name"

                if "theme_color" in m_data and m_data["theme_color"]:
                    blueprint["theme_color"] = cls._normalize_hex_color(m_data["theme_color"])
                    blueprint["detection_sources"]["theme_color"] = "manifest.json theme_color"
                elif "background_color" in m_data and m_data["background_color"]:
                    blueprint["theme_color"] = cls._normalize_hex_color(m_data["background_color"])

                if "orientation" in m_data:
                    ori = m_data["orientation"].lower()
                    if "landscape" in ori:
                        blueprint["orientation"] = "landscape"
                        blueprint["detection_sources"]["orientation"] = "manifest.json orientation"
                    elif "portrait" in ori:
                        blueprint["orientation"] = "portrait"
                        blueprint["detection_sources"]["orientation"] = "manifest.json orientation"

                if "display" in m_data:
                    disp = m_data["display"].lower()
                    blueprint["is_fullscreen"] = (disp in ["fullscreen", "standalone"])

                m_icons = m_data.get("icons", [])
                for mic in reversed(m_icons):
                    if "src" in mic:
                        candidate_file = (manifest_files[0].parent / mic["src"]).resolve()
                        if candidate_file.exists():
                            manifest_icon_candidates.append(candidate_file)
            except Exception:
                pass

        # 3. Scan HTML Files (index.html or others)
        html_files = list(dir_path.glob("**/*.html"))
        if html_files:
            # Sort to inspect index.html first
            html_files.sort(key=lambda p: 0 if p.name.lower() == "index.html" else 1)
            primary_html = html_files[0]
            try:
                html_text = primary_html.read_text(encoding="utf-8", errors="ignore")
                title_match = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.IGNORECASE | re.DOTALL)
                if title_match and ("app_name" not in blueprint["detection_sources"] or blueprint["app_name"] == default_app_name):
                    clean_t = re.split(r"[-|•–—:»]", title_match.group(1).strip())[0].strip()
                    if clean_t:
                        blueprint["app_name"] = clean_t
                        blueprint["detection_sources"]["app_name"] = "index.html <title>"

                theme_meta = re.search(r'<meta\s+name=["\']theme-color["\']\s+content=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
                if theme_meta and "theme_color" not in blueprint["detection_sources"]:
                    col = theme_meta.group(1).strip()
                    if re.match(r"^#(?:[0-9a-fA-F]{3}){1,2}$", col):
                        blueprint["theme_color"] = cls._normalize_hex_color(col)
                        blueprint["detection_sources"]["theme_color"] = "HTML meta theme-color"
            except Exception:
                pass

        # 4. Scan CSS Files for Theme Colors
        if "theme_color" not in blueprint["detection_sources"]:
            for css_file in list(dir_path.glob("**/*.css"))[:10]:
                try:
                    css_txt = css_file.read_text(encoding="utf-8", errors="ignore")
                    var_match = re.search(r'(?:--primary|--theme|--main-color|--bg-color|--background):\s*(#[0-9a-fA-F]{3,8})', css_txt)
                    if var_match:
                        blueprint["theme_color"] = cls._normalize_hex_color(var_match.group(1))
                        blueprint["detection_sources"]["theme_color"] = f"CSS variable in {css_file.name}"
                        break
                except Exception:
                    pass

        # 5. Scan JS/HTML for Permissions & Game Engines
        all_code_files = list(dir_path.glob("**/*.js")) + list(dir_path.glob("**/*.html")) + list(dir_path.glob("**/*.ts"))
        for code_file in all_code_files[:60]:
            try:
                code_txt = code_file.read_text(encoding="utf-8", errors="ignore")
                
                # Check permissions
                for perm, patterns in cls.PERMISSION_PATTERNS.items():
                    if perm not in blueprint["detected_permissions"]:
                        for pat in patterns:
                            if re.search(pat, code_txt, re.IGNORECASE):
                                blueprint["detected_permissions"].append(perm)
                                break

                # Check game engines & landscape orientation
                if blueprint["orientation"] == "sensor":
                    for g_pat in cls.GAME_FRAMEWORK_PATTERNS:
                        if re.search(g_pat, code_txt, re.IGNORECASE):
                            blueprint["orientation"] = "landscape"
                            blueprint["is_fullscreen"] = True
                            blueprint["detection_sources"]["orientation"] = f"Canvas/Game engine in {code_file.name}"
                            blueprint["framework"] = "HTML5 Game / WebGL Canvas"
                            break
            except Exception:
                pass

        # 6. Discover and Normalize Application Icon
        icon_file = cls._find_best_local_icon(dir_path, manifest_icon_candidates, blueprint["app_name"])
        if icon_file and icon_file.exists():
            blueprint["icon_path"] = str(icon_file)
            blueprint["icon_base64"] = cls._file_to_base64(icon_file)
            blueprint["detection_sources"]["icon"] = f"Discovered asset ({icon_file.name})"
        else:
            fallback_img = IconGenerator._create_fallback_icon(blueprint["app_name"], 512)
            safe_slug = re.sub(r'[^a-zA-Z0-9]', '_', blueprint["app_name"])
            fallback_path = ICONS_DIR / f"icon_{safe_slug}.png"
            fallback_img.save(fallback_path, "PNG")
            blueprint["icon_path"] = str(fallback_path)
            blueprint["icon_base64"] = cls._file_to_base64(fallback_path)
            blueprint["detection_sources"]["icon"] = "Synthesized Adaptive Badge"

        # Update package name slug based on final app name
        final_clean_slug = re.sub(r'[^a-zA-Z0-9]', '', blueprint["app_name"].lower()) or "app"
        blueprint["package_name"] = f"com.web2apk.{final_clean_slug}"

        return blueprint

    @classmethod
    def inspect_zip(cls, zip_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Unpacks a ZIP archive into a temp folder and runs deep directory inspection.
        """
        zip_path = Path(zip_path).resolve()
        temp_dir = Path(tempfile.mkdtemp(prefix="inspect_zip_"))
        try:
            import zipfile
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extractall(temp_dir)
            blueprint = cls.inspect_directory(temp_dir)
            blueprint["source_type"] = "zip"
            blueprint["zip_name"] = zip_path.name
            return blueprint
        finally:
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass

    @classmethod
    def _find_best_local_icon(
        cls,
        dir_path: Path,
        manifest_candidates: List[Path],
        app_name: str
    ) -> Optional[Path]:
        """
        Finds the best local icon or logo in the directory.
        Supports SVG (vector graphics), PNG, WebP, JPG, ICO, and inline HTML SVGs.
        """
        candidates = list(manifest_candidates)

        # Standard icon and logo filenames
        icon_names = [
            "logo.svg", "icon.svg", "favicon.svg", "app-icon.svg", "brand.svg",
            "icon-512.png", "icon-512x512.png", "icon-192.png", "icon-192x192.png",
            "apple-touch-icon.png", "apple-touch-icon-precomposed.png",
            "logo.png", "icon.png", "app-icon.png", "favicon.png",
            "favicon.ico", "logo.webp", "icon.webp"
        ]

        for name in icon_names:
            matches = list(dir_path.glob(f"**/{name}"))
            candidates.extend(matches)

        # Look for any image or SVG in common asset folders
        for ext in ["*.svg", "*.png", "*.webp", "*.jpg", "*.jpeg", "*.ico"]:
            candidates.extend(list(dir_path.glob(f"**/icons/{ext}")))
            candidates.extend(list(dir_path.glob(f"**/icon/{ext}")))
            candidates.extend(list(dir_path.glob(f"**/logo/{ext}")))
            candidates.extend(list(dir_path.glob(f"**/logos/{ext}")))
            candidates.extend(list(dir_path.glob(f"**/brand/{ext}")))
            candidates.extend(list(dir_path.glob(f"**/assets/{ext}")))
            candidates.extend(list(dir_path.glob(f"**/public/{ext}")))

        # Scan HTML files for <img> logos or inline <svg> logos
        for html_file in list(dir_path.glob("**/*.html"))[:10]:
            try:
                html_txt = html_file.read_text(encoding="utf-8", errors="ignore")
                # Look for <img> tags referencing logos
                img_logo_matches = re.findall(r'<img[^>]+(?:class|id|alt|src)=["\'][^"\']*(?:logo|brand|icon)[^"\']*["\'][^>]*>', html_txt, re.IGNORECASE)
                for img_tag in img_logo_matches:
                    src_m = re.search(r'src=["\']([^"\']+)["\']', img_tag)
                    if src_m:
                        src_val = src_m.group(1)
                        if not src_val.startswith(("http://", "https://", "data:")):
                            cand_p = (html_file.parent / src_val).resolve()
                            if cand_p.exists() and cand_p.is_file():
                                candidates.append(cand_p)

                # Look for inline <svg> logos
                svg_matches = re.findall(r'(<svg[^>]+(?:class|id|aria-label)=["\'][^"\']*(?:logo|brand)[^"\']*["\'][^>]*>.*?</svg>)', html_txt, re.IGNORECASE | re.DOTALL)
                if svg_matches:
                    for idx, svg_markup in enumerate(svg_matches[:3]):
                        svg_file = ICONS_DIR / f"inline_{re.sub(r'[^a-zA-Z0-9]', '_', app_name)}_{idx}.svg"
                        svg_file.write_text(svg_markup, encoding="utf-8")
                        candidates.append(svg_file)
            except Exception:
                pass

        # Deduplicate candidates
        valid_icons = []
        seen = set()
        for cand in candidates:
            cand_resolved = cand.resolve()
            if cand_resolved not in seen and cand_resolved.exists() and cand_resolved.is_file() and cand_resolved.stat().st_size > 30:
                seen.add(cand_resolved)
                valid_icons.append(cand_resolved)

        if not valid_icons:
            return None

        # Score candidates: SVGs and files with "logo" or "icon" in name are preferred
        best_score = -1
        best_cand = None

        for cand in valid_icons:
            name_lower = cand.name.lower()
            cand_score = 0
            is_named_logo = any(k in name_lower for k in ["logo", "icon", "brand", "app"])

            if cand.suffix.lower() == ".svg":
                # Vector format is premier quality for infinite resolution scaling
                cand_score = 2000000 + (500000 if is_named_logo else 0)
            elif cand.suffix.lower() == ".ico":
                cand_score = 50000
            else:
                try:
                    with Image.open(cand) as img:
                        cand_score = img.width * img.height
                        if is_named_logo:
                            cand_score *= 2
                except Exception:
                    continue

            if cand_score > best_score:
                best_score = cand_score
                best_cand = cand

        if best_cand:
            try:
                dest_path = ICONS_DIR / f"local_{re.sub(r'[^a-zA-Z0-9]', '_', app_name)}.png"
                norm_img = IconGenerator.load_and_normalize_image(best_cand, 512, app_name)
                norm_img.save(dest_path, "PNG")
                return dest_path
            except Exception as e:
                print(f"[AppInspector] Icon normalization error: {e}")
                return best_cand

        return None

    @classmethod
    def _download_and_normalize_icon(cls, urls: List[str], domain: str, app_name: str) -> Optional[Path]:
        """
        Downloads icon candidate URLs (SVG, PNG, WebP, ICO, JPG, Data URIs)
        and saves normalized 512x512 square PNG.
        """
        safe_domain = re.sub(r'[^a-zA-Z0-9]', '_', domain)
        dest_path = ICONS_DIR / f"logo_{safe_domain}.png"

        for icon_url in urls:
            try:
                # Handle Data URI (e.g. data:image/svg+xml;...)
                if icon_url.startswith("data:"):
                    norm_img = IconGenerator.load_and_normalize_image(icon_url, 512, app_name)
                    if norm_img and norm_img.width == 512 and norm_img.height == 512:
                        norm_img.save(dest_path, "PNG")
                        return dest_path

                safe, _ = SSRFProtector.is_url_safe(icon_url)
                if not safe:
                    continue

                resp = requests.get(icon_url, headers=cls.HEADERS, timeout=4, verify=False)
                if resp.status_code != 200 or len(resp.content) < 30:
                    continue

                norm_img = IconGenerator.load_and_normalize_image(resp.content, 512, app_name)
                if norm_img and norm_img.width == 512 and norm_img.height == 512:
                    norm_img.save(dest_path, "PNG")
                    return dest_path
            except Exception:
                continue

        return None

    @staticmethod
    def _normalize_hex_color(col: str) -> str:
        col = col.strip()
        if col.startswith("#"):
            if len(col) == 4: # #rgb -> #rrggbb
                return f"#{col[1]*2}{col[2]*2}{col[3]*2}"
            elif len(col) >= 7:
                return col[:7]
        return "#0f172a"

    @staticmethod
    def _file_to_base64(file_path: Path) -> Optional[str]:
        try:
            with open(file_path, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")
                return f"data:image/png;base64,{data}"
        except Exception:
            return None

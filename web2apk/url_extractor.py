import os
import re
import io
import json
import urllib.parse
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image

from .security.server_shield import SSRFProtector

CACHE_DIR = Path.home() / ".web2apk" / "url_cache"

class URLExtractor:
    """
    Crawls and extracts website metadata, brand logos, apple-touch-icons,
    web app manifest icons, and theme colors with SSRF Shield protection.
    """

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8"
    }

    @classmethod
    def inspect_url(cls, url: str) -> Dict[str, Any]:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"https://{url}"

        # 1. Validate Target URL with SSRF Shield
        safe, reason = SSRFProtector.is_url_safe(url)
        if not safe:
            raise ValueError(f"[CyberShield] {reason}")

        parsed_url = urllib.parse.urlparse(url)
        domain = parsed_url.netloc
        scheme = parsed_url.scheme
        base_url = f"{scheme}://{domain}"

        result = {
            "url": url,
            "domain": domain,
            "title": domain.replace("www.", "").split(".")[0].title(),
            "theme_color": "#0f172a",
            "description": "",
            "logo_url": None,
            "local_logo_path": None
        }

        candidate_urls = []

        try:
            resp = requests.get(url, headers=cls.HEADERS, timeout=6, verify=False)
            html = resp.text

            # 1. Extract Title
            title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
            if title_match:
                raw_title = title_match.group(1).strip()
                clean_title = re.split(r"[-|•–—]", raw_title)[0].strip()
                if clean_title:
                    result["title"] = clean_title

            # 2. Extract Theme Color
            theme_match = re.search(r'<meta\s+name=["\']theme-color["\']\s+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
            if not theme_match:
                theme_match = re.search(r'<meta\s+content=["\']([^"\']+)["\']\s+name=["\']theme-color["\']', html, re.IGNORECASE)
            if theme_match:
                result["theme_color"] = theme_match.group(1).strip()

            # 3. Discover Best Icon Candidates
            # A. Web App Manifest
            manifest_match = re.search(r'<link\s+rel=["\']manifest["\']\s+href=["\']([^"\']+)["\']', html, re.IGNORECASE)
            if manifest_match:
                m_href = manifest_match.group(1)
                m_url = urllib.parse.urljoin(url, m_href)
                m_safe, _ = SSRFProtector.is_url_safe(m_url)
                if m_safe:
                    try:
                        m_resp = requests.get(m_url, headers=cls.HEADERS, timeout=4, verify=False)
                        m_json = m_resp.json()
                        icons = m_json.get("icons", [])
                        for ic in reversed(icons):
                            if "src" in ic:
                                candidate_urls.append(urllib.parse.urljoin(m_url, ic["src"]))
                    except Exception:
                        pass

            # B. Apple Touch Icon
            apple_matches = re.findall(r'<link\s+[^>]*rel=["\']apple-touch-icon(?:-precomposed)?["\'][^>]*href=["\']([^"\']+)["\']', html, re.IGNORECASE)
            for am in apple_matches:
                candidate_urls.append(urllib.parse.urljoin(url, am))

            # C. OpenGraph Image
            og_match = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', html, re.IGNORECASE)
            if og_match:
                candidate_urls.append(urllib.parse.urljoin(url, og_match.group(1)))

            # D. Standard Icon / Shortcut Icon
            icon_matches = re.findall(r'<link\s+[^>]*rel=["\'](?:shortcut\s+)?icon["\'][^>]*href=["\']([^"\']+)["\']', html, re.IGNORECASE)
            for im in icon_matches:
                candidate_urls.append(urllib.parse.urljoin(url, im))

        except Exception as e:
            print(f"[URLExtractor] Warning inspecting {url}: {e}")

        # E. Google & DuckDuckGo Favicon Services Fallback
        candidate_urls.append(f"https://www.google.com/s2/favicons?domain={domain}&sz=512")
        candidate_urls.append(f"https://icons.duckduckgo.com/ip3/{domain}.ico")
        candidate_urls.append(f"{base_url}/favicon.ico")

        # 4. Download and Validate Highest Quality Logo
        local_logo = cls._download_best_logo(candidate_urls, domain)
        if local_logo:
            result["local_logo_path"] = str(local_logo)
            result["logo_url"] = candidate_urls[0] if candidate_urls else None

        return result

    @classmethod
    def _download_best_logo(cls, candidate_urls: list, domain: str) -> Optional[Path]:
        safe_domain = re.sub(r'[^a-zA-Z0-9]', '_', domain)
        dest_path = CACHE_DIR / f"logo_{safe_domain}.png"

        for cand_url in candidate_urls:
            try:
                cand_safe, _ = SSRFProtector.is_url_safe(cand_url)
                if not cand_safe:
                    continue

                resp = requests.get(cand_url, headers=cls.HEADERS, timeout=4, verify=False)
                if resp.status_code != 200 or len(resp.content) < 100:
                    continue

                img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
                
                if img.width < 128 or img.height < 128:
                    framed = Image.new("RGBA", (512, 512), (15, 23, 42, 255))
                    scale_factor = 280 / max(img.width, img.height)
                    new_w, new_h = int(img.width * scale_factor), int(img.height * scale_factor)
                    resized_ic = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    framed.paste(resized_ic, ((512 - new_w) // 2, (512 - new_h) // 2), resized_ic)
                    framed.save(dest_path, "PNG")
                else:
                    img.save(dest_path, "PNG")

                return dest_path
            except Exception:
                continue

        return None

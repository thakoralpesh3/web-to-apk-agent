import os
import io
import re
import base64
import urllib.parse
from pathlib import Path
from typing import Optional, Union
import requests
from PIL import Image, ImageDraw, ImageFont

class IconGenerator:
    """
    Generates all Android mipmap launcher icons and Android TV Leanback banners (320x180).
    Supports rasterizing SVG (vector graphics), Data URIs, ICO multi-resolution icons,
    and all standard web image formats (PNG, JPG, WebP, GIF) into crisp Android icons.
    """

    MIPMAP_SIZES = {
        "mipmap-mdpi": 48,
        "mipmap-hdpi": 72,
        "mipmap-xhdpi": 96,
        "mipmap-xxhdpi": 144,
        "mipmap-xxxhdpi": 192,
    }

    @staticmethod
    def _create_fallback_icon(app_name: str, size: int = 512) -> Image.Image:
        """
        Generates a beautiful modern gradient icon with initial letters.
        """
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Draw rounded squircle / modern icon base
        radius = int(size * 0.22)
        # Background gradient simulation
        for i in range(size):
            alpha = int(255 * (1 - (i / size) * 0.3))
            # Indigo to Cyan gradient
            r = int(14 + (56 - 14) * (i / size))
            g = int(165 - (165 - 189) * (i / size))
            b = int(233 + (248 - 233) * (i / size))
        
        # Solid squircle with smooth border
        box = [(0, 0), (size, size)]
        draw.rounded_rectangle(box, radius=radius, fill=(24, 24, 27, 255), outline=(56, 189, 248, 255), width=int(size * 0.03))

        # Inner decorative circle
        margin = int(size * 0.15)
        draw.ellipse([(margin, margin), (size - margin, size - margin)], fill=(39, 39, 42, 255), outline=(99, 102, 241, 180), width=int(size * 0.02))

        # Initial letter text
        initials = "".join([w[0].upper() for w in app_name.split()[:2]]) if app_name else "APK"
        if not initials:
            initials = "W"

        # Try to load a truetype font, or fallback to default
        font_size = int(size * 0.35)
        font = None
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf"
        ]
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    font = ImageFont.truetype(fp, font_size)
                    break
                except Exception:
                    pass
        if not font:
            font = ImageFont.load_default()

        # Draw centered text
        bbox = draw.textbbox((0, 0), initials, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        text_x = (size - text_w) / 2
        text_y = (size - text_h) / 2 - (bbox[1])
        draw.text((text_x, text_y), initials, fill=(255, 255, 255, 255), font=font)

        return img

    @classmethod
    def rasterize_svg(cls, svg_data: Union[str, bytes, Path], output_size: int = 512) -> Optional[Image.Image]:
        """
        Renders SVG vector data into high-resolution RGBA Image using CairoSVG.
        """
        try:
            import cairosvg
            if isinstance(svg_data, Path):
                with open(svg_data, "rb") as f:
                    svg_bytes = f.read()
            elif isinstance(svg_data, str):
                if os.path.exists(svg_data):
                    with open(svg_data, "rb") as f:
                        svg_bytes = f.read()
                else:
                    svg_bytes = svg_data.encode("utf-8")
            else:
                svg_bytes = svg_data

            png_bytes = cairosvg.svg2png(bytestring=svg_bytes, output_width=output_size, output_height=output_size)
            if png_bytes:
                return Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        except Exception as e:
            print(f"[IconGenerator] SVG rasterization warning: {e}")
        return None

    @classmethod
    def _normalize_canvas(cls, img: Image.Image, target_size: int = 512) -> Image.Image:
        """
        Centers and scales any image onto a target square canvas.
        """
        w, h = img.width, img.height
        if w == target_size and h == target_size:
            return img

        canvas = Image.new("RGBA", (target_size, target_size), (0, 0, 0, 0))
        scale = (target_size * 0.94) / max(w, h)
        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
        resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
        pos = ((target_size - nw) // 2, (target_size - nh) // 2)
        canvas.paste(resized, pos, resized)
        return canvas

    @classmethod
    def load_and_normalize_image(
        cls,
        source: Optional[Union[str, Path, bytes, Image.Image]],
        target_size: int = 512,
        app_name: str = "Web App"
    ) -> Image.Image:
        """
        Robust multi-format loader:
        Supports PNG, JPG, JPEG, WEBP, ICO, GIF, BMP, SVG files, SVG data URIs, raw SVG XML,
        and remote HTTP/HTTPS image/SVG URLs.
        Normalizes output into a crisp, centered, square RGBA canvas.
        """
        if not source:
            return cls._create_fallback_icon(app_name, target_size)

        if isinstance(source, Image.Image):
            return cls._normalize_canvas(source.convert("RGBA"), target_size)

        # Handle bytes
        if isinstance(source, bytes):
            trimmed = source.lstrip()
            if trimmed.startswith(b"<svg") or (b"<?xml" in trimmed and b"<svg" in trimmed) or b"<svg" in trimmed[:300]:
                svg_img = cls.rasterize_svg(source, target_size)
                if svg_img:
                    return cls._normalize_canvas(svg_img, target_size)
            try:
                img = Image.open(io.BytesIO(source)).convert("RGBA")
                return cls._normalize_canvas(img, target_size)
            except Exception:
                return cls._create_fallback_icon(app_name, target_size)

        source_str = str(source).strip()

        # Handle Data URI
        if source_str.startswith("data:"):
            try:
                header, encoded = source_str.split(",", 1)
                if ";base64" in header:
                    raw_data = base64.b64decode(encoded)
                else:
                    raw_data = urllib.parse.unquote(encoded).encode("utf-8")

                if "image/svg+xml" in header or b"<svg" in raw_data[:300]:
                    svg_img = cls.rasterize_svg(raw_data, target_size)
                    if svg_img:
                        return cls._normalize_canvas(svg_img, target_size)
                img = Image.open(io.BytesIO(raw_data)).convert("RGBA")
                return cls._normalize_canvas(img, target_size)
            except Exception as e:
                print(f"[IconGenerator] Data URI decode error: {e}")
                return cls._create_fallback_icon(app_name, target_size)

        # Handle Remote URL
        if source_str.startswith("http://") or source_str.startswith("https://"):
            try:
                resp = requests.get(source_str, timeout=6, headers={"User-Agent": "Mozilla/5.0"}, verify=False)
                if resp.status_code == 200 and len(resp.content) > 20:
                    return cls.load_and_normalize_image(resp.content, target_size, app_name)
            except Exception as e:
                print(f"[IconGenerator] URL download warning for {source_str}: {e}")
                return cls._create_fallback_icon(app_name, target_size)

        # Handle raw SVG markup string
        if source_str.startswith("<svg") or ("<?xml" in source_str and "<svg" in source_str):
            svg_img = cls.rasterize_svg(source_str, target_size)
            if svg_img:
                return cls._normalize_canvas(svg_img, target_size)

        file_path = Path(source_str).resolve()
        if file_path.exists() and file_path.is_file():
            # Check for SVG extension or SVG header
            if file_path.suffix.lower() == ".svg":
                svg_img = cls.rasterize_svg(file_path, target_size)
                if svg_img:
                    return cls._normalize_canvas(svg_img, target_size)

            try:
                with open(file_path, "rb") as f:
                    head = f.read(300)
                    if b"<svg" in head or (b"<?xml" in head and b"<svg" in head):
                        svg_img = cls.rasterize_svg(file_path, target_size)
                        if svg_img:
                            return cls._normalize_canvas(svg_img, target_size)
            except Exception:
                pass

            # Check ICO multi-frame
            if file_path.suffix.lower() == ".ico":
                try:
                    with Image.open(file_path) as ico:
                        best_frame = None
                        max_dim = -1
                        n_frames = getattr(ico, 'n_frames', 1)
                        for i in range(n_frames):
                            try:
                                ico.seek(i)
                                if ico.width * ico.height > max_dim:
                                    max_dim = ico.width * ico.height
                                    best_frame = ico.copy().convert("RGBA")
                            except Exception:
                                pass
                        if best_frame:
                            return cls._normalize_canvas(best_frame, target_size)
                except Exception:
                    pass

            # Standard Image
            try:
                with Image.open(file_path) as img:
                    rgba = img.convert("RGBA")
                    return cls._normalize_canvas(rgba, target_size)
            except Exception as e:
                print(f"[IconGenerator] Image open error {file_path}: {e}")

        return cls._create_fallback_icon(app_name, target_size)

    @classmethod
    def generate_icons(
        cls,
        res_dir: str,
        source_icon_path: Optional[str] = None,
        app_name: str = "Web App"
    ) -> bool:
        """
        Generates standard Android mipmaps and TV banner in the target Android res/ directory.
        Supports any image format, vector SVG, data URIs, or local/remote paths.
        """
        res_path = Path(res_dir)
        res_path.mkdir(parents=True, exist_ok=True)

        base_img = cls.load_and_normalize_image(source_icon_path, 512, app_name)

        # 1. Generate all mipmap launcher icons
        for mipmap_name, size in cls.MIPMAP_SIZES.items():
            folder = res_path / mipmap_name
            folder.mkdir(parents=True, exist_ok=True)
            
            resized = base_img.resize((size, size), Image.Resampling.LANCZOS)
            resized.save(folder / "ic_launcher.png", "PNG")
            # Round icon variant
            resized.save(folder / "ic_launcher_round.png", "PNG")

        # 2. Generate Android TV Leanback Banner (320x180)
        drawable_folder = res_path / "drawable-xhdpi"
        drawable_folder.mkdir(parents=True, exist_ok=True)
        
        banner_w, banner_h = 320, 180
        banner_img = Image.new("RGBA", (banner_w, banner_h), (18, 18, 24, 255))
        bdraw = ImageDraw.Draw(banner_img)

        # Draw subtle gradient accent line
        bdraw.rectangle([(0, banner_h - 6), (banner_w, banner_h)], fill=(56, 189, 248, 255))

        # Paste icon on left
        icon_size = 120
        banner_icon = base_img.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
        icon_x = 24
        icon_y = (banner_h - icon_size) // 2
        banner_img.paste(banner_icon, (icon_x, icon_y), banner_icon)

        # Draw App Name text on right
        font_size = 22
        font = None
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf"
        ]
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    font = ImageFont.truetype(fp, font_size)
                    break
                except Exception:
                    pass
        if not font:
            font = ImageFont.load_default()

        # Truncate text if too long
        display_name = app_name if len(app_name) <= 16 else app_name[:14] + "..."
        bdraw.text((icon_x + icon_size + 16, banner_h // 2 - 14), display_name, fill=(255, 255, 255, 255), font=font)
        
        # Subtext "APP"
        sub_font_size = 12
        sub_font = None
        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    sub_font = ImageFont.truetype(fp, sub_font_size)
                    break
                except Exception:
                    pass
        if not sub_font:
            sub_font = font
        bdraw.text((icon_x + icon_size + 16, banner_h // 2 + 14), "ANDROID TV EDITION", fill=(148, 163, 184, 255), font=sub_font)

        banner_img.save(drawable_folder / "tv_banner.png", "PNG")
        
        # Also copy standard drawable for non-xhdpi TV fallback
        def_drawable = res_path / "drawable"
        def_drawable.mkdir(parents=True, exist_ok=True)
        banner_img.save(def_drawable / "tv_banner.png", "PNG")

        return True

import io
import os
import re
import socket
import base64
import urllib.parse
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Union, Tuple
import qrcode


class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True


class QRServer:
    """
    Generates QR codes, local LAN URLs, and runs an embedded high-speed
    Wi-Fi sideloading server for instant installation onto Smartphones and Android TVs.
    """

    @staticmethod
    def get_local_ip() -> str:
        """
        Detects primary local LAN IP address accessible by other devices on the same Wi-Fi.
        """
        # 1. Try connecting to an external target (UDP, doesn't send actual packet)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            if ip and not ip.startswith("127."):
                return ip
        except Exception:
            pass

        # 2. Try inspecting hostname addresses
        try:
            hostname = socket.gethostname()
            for info in socket.getaddrinfo(hostname, None):
                candidate_ip = info[4][0]
                if ":" not in candidate_ip and not candidate_ip.startswith("127."):
                    return candidate_ip
        except Exception:
            pass

        return "127.0.0.1"

    @classmethod
    def get_download_url(cls, apk_name: str, port: int = 8990, host: Optional[str] = None) -> str:
        """
        Returns full HTTP download URL for an APK.
        """
        if host and "localhost" not in host and "127.0.0.1" not in host:
            clean_host = host.rstrip("/")
            if not clean_host.startswith("http://") and not clean_host.startswith("https://"):
                clean_host = f"http://{clean_host}"
            return f"{clean_host}/download/{apk_name}"

        ip = cls.get_local_ip()
        return f"http://{ip}:{port}/download/{apk_name}"

    @classmethod
    def generate_terminal_qr(cls, text: str):
        """
        Prints high-contrast QR code directly to terminal.
        """
        qr = qrcode.QRCode(box_size=1, border=1)
        qr.add_data(text)
        qr.make()
        qr.print_ascii(invert=True)

    @classmethod
    def generate_qr_base64(cls, text: str) -> str:
        """
        Returns base64 encoded PNG for display in Web GUI.
        """
        qr = qrcode.QRCode(box_size=10, border=2)
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#38bdf8", back_color="#0f172a")

        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"

    @classmethod
    def generate_landing_page_html(cls, apk_name: str, apk_size_mb: float = 0, app_name: str = "") -> str:
        """
        Produces a mobile-responsive landing page that reliably triggers
        APK downloading on mobile browsers and camera QR scanners,
        supporting dedicated options for Smartphones and Android TV.
        """
        output_dir = Path.home() / "Web2APK_Output"
        display_title = app_name or apk_name.replace("-universal.apk", "").replace("-android-tv.apk", "").replace("-smartphone.apk", "").replace(".apk", "").replace("_", " ")

        base_prefix = re.sub(r'-(universal|smartphone|android-tv)\.apk$', '', apk_name)
        phone_name = f"{base_prefix}-smartphone.apk"
        tv_name = f"{base_prefix}-android-tv.apk"

        has_phone = (output_dir / phone_name).exists()
        has_tv = (output_dir / tv_name).exists()

        phone_size = round((output_dir / phone_name).stat().st_size / (1024 * 1024), 2) if has_phone else apk_size_mb
        tv_size = round((output_dir / tv_name).stat().st_size / (1024 * 1024), 2) if has_tv else apk_size_mb

        raw_download_url = f"/download-raw/{urllib.parse.quote(apk_name)}"
        phone_url = f"/download-raw/{urllib.parse.quote(phone_name)}"
        tv_url = f"/download-raw/{urllib.parse.quote(tv_name)}"

        is_specifically_tv = "-android-tv.apk" in apk_name
        is_specifically_phone = "-smartphone.apk" in apk_name

        if has_phone and has_tv:
            buttons_html = f"""
        <div style="display: flex; flex-direction: column; gap: 12px; margin-bottom: 16px;">
            <a id="btn-phone" href="{phone_url}" class="btn-download btn-phone" style="background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%);">
                <div style="font-size: 1.05rem; font-weight: 700;">📱 Download for Android Phone</div>
                <div style="font-size: 0.75rem; opacity: 0.88; margin-top: 3px;">Phones & Tablets (Touchscreen) • {phone_size} MB</div>
            </a>
            <a id="btn-tv" href="{tv_url}" class="btn-download btn-tv" style="background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%);">
                <div style="font-size: 1.05rem; font-weight: 700;">📺 Download for Android TV</div>
                <div style="font-size: 0.75rem; opacity: 0.88; margin-top: 3px;">Smart TV, Google TV & Remote Cursor • {tv_size} MB</div>
            </a>
        </div>
            """
            auto_trigger_script = f"""
        // Smart device detection for dual APK package
        var isTV = /googletv|smarttv|androidtv|large screen|boxee|kylo/i.test(navigator.userAgent);
        var autoUrl = isTV ? "{tv_url}" : "{phone_url}";
        if ("{apk_name}".includes("-smartphone.apk")) autoUrl = "{phone_url}";
        if ("{apk_name}".includes("-android-tv.apk")) autoUrl = "{tv_url}";

        setTimeout(function() {{
            try {{
                window.location.href = autoUrl;
                document.getElementById("status-msg").innerText = (isTV ? "Android TV" : "Android Phone") + " APK download starting...";
            }} catch(e) {{
                document.getElementById("status-msg").innerText = "Select your device above to begin download.";
            }}
        }}, 600);
            """
        else:
            single_label = "📺 Download for Android TV" if is_specifically_tv else "📱 Download for Android Phone"
            subtitle = "Smart TV, Google TV & Remote Cursor" if is_specifically_tv else "Phones & Tablets (Touchscreen)"
            buttons_html = f"""
        <a id="download-link" href="{raw_download_url}" class="btn-download" style="background: {'linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%)' if is_specifically_tv else 'linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%)'};">
            <div style="font-size: 1.05rem; font-weight: 700;">{single_label}</div>
            <div style="font-size: 0.75rem; opacity: 0.88; margin-top: 3px;">{subtitle} • {apk_size_mb} MB</div>
        </a>
            """
            auto_trigger_script = f"""
        setTimeout(function() {{
            try {{
                window.location.href = "{raw_download_url}";
                document.getElementById("status-msg").innerText = "Downloading started. Tap above if not started.";
            }} catch(e) {{
                document.getElementById("status-msg").innerText = "Tap the button above to begin download.";
            }}
        }}, 600);
            """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Install {display_title}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: radial-gradient(circle at center, #1e293b 0%, #090d16 100%);
            color: #f8fafc;
            font-family: system-ui, -apple-system, sans-serif;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .card {{
            background: rgba(15, 23, 42, 0.9);
            border: 1px solid rgba(56, 189, 248, 0.3);
            border-radius: 28px;
            padding: 32px 24px;
            max-width: 460px;
            width: 100%;
            text-align: center;
            box-shadow: 0 10px 40px rgba(0,0,0,0.6), 0 0 30px rgba(56, 189, 248, 0.2);
        }}
        .icon-badge {{
            width: 80px;
            height: 80px;
            border-radius: 20px;
            background: linear-gradient(135deg, #0284c7 0%, #6366f1 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 20px auto;
            box-shadow: 0 8px 24px rgba(99, 102, 241, 0.4);
        }}
        .icon-badge svg {{
            width: 44px;
            height: 44px;
            fill: #ffffff;
        }}
        h1 {{
            font-size: 1.4rem;
            font-weight: 700;
            color: #ffffff;
            margin-bottom: 6px;
        }}
        .meta-pills {{
            display: flex;
            gap: 8px;
            justify-content: center;
            margin-bottom: 24px;
            flex-wrap: wrap;
        }}
        .pill {{
            font-size: 0.75rem;
            font-weight: 600;
            padding: 4px 12px;
            border-radius: 9999px;
            background: rgba(56, 189, 248, 0.15);
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.3);
        }}
        .btn-download {{
            display: block;
            width: 100%;
            background: linear-gradient(135deg, #38bdf8 0%, #2563eb 100%);
            color: #ffffff;
            text-decoration: none;
            font-weight: 700;
            font-size: 1rem;
            padding: 16px;
            border-radius: 16px;
            box-shadow: 0 4px 20px rgba(37, 99, 235, 0.5);
            transition: transform 0.15s ease;
        }}
        .btn-download:active {{
            transform: scale(0.98);
        }}
        .status-text {{
            font-size: 0.85rem;
            color: #94a3b8;
            margin-bottom: 20px;
            min-height: 20px;
        }}
        .guide-box {{
            background: rgba(30, 41, 59, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
            padding: 16px;
            text-align: left;
            font-size: 0.8rem;
            color: #cbd5e1;
            line-height: 1.5;
        }}
        .guide-box h4 {{
            font-size: 0.85rem;
            color: #38bdf8;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        .guide-box ol {{
            padding-left: 20px;
        }}
        .guide-box li {{
            margin-bottom: 6px;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon-badge">
            <svg viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14.5v-9l6 4.5-6 4.5z"/></svg>
        </div>
        <h1>{display_title}</h1>
        <div class="meta-pills">
            <span class="pill">APK Package</span>
            <span class="pill">{apk_size_mb} MB</span>
            <span class="pill">Android 5.0 - 15</span>
        </div>

        {buttons_html}

        <div class="status-text" id="status-msg">
            Download starting automatically...
        </div>

        <div class="guide-box">
            <h4>💡 How to Install on Android:</h4>
            <ol>
                <li>Tap <strong>"Download"</strong> or <strong>"Download anyway"</strong> if prompted.</li>
                <li>When download finishes, tap the notification to <strong>Open</strong>.</li>
                <li>If prompted with <em>"Install unknown apps"</em>, tap <strong>Settings</strong> and enable <strong>Allow from this source</strong>, then tap <strong>Install</strong>.</li>
            </ol>
        </div>
    </div>

    <script>
        {auto_trigger_script}
    </script>
</body>
</html>"""

    @classmethod
    def serve_apk(
        cls,
        apk_path: Union[str, Path],
        port: int = 8990,
        blocking: bool = True,
        on_ready: Optional[callable] = None
    ) -> Tuple[HTTPServer, int]:
        """
        Starts an HTTP server to serve the APK and mobile landing page.
        Supports both blocking mode (for CLI) and non-blocking background thread.
        """
        target_path = Path(apk_path).resolve()
        if not target_path.exists():
            raise FileNotFoundError(f"APK not found at: {apk_path}")

        apk_name = target_path.name
        apk_size_mb = round(target_path.stat().st_size / (1024 * 1024), 2)
        clean_app_name = (
            apk_name.replace("-smartphone.apk", "")
            .replace("-android-tv.apk", "")
            .replace("-universal.apk", "")
            .replace(".apk", "")
            .replace("_", " ")
        )

        class SideloadHTTPHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # Suppress default noisy console logs

            def do_GET(self):
                parsed = urllib.parse.urlparse(self.path)
                req_path = urllib.parse.unquote(parsed.path)
                query = parsed.query
                accept_header = self.headers.get("Accept", "").lower()
                user_agent = self.headers.get("User-Agent", "").lower()

                # Direct binary download condition:
                # 1. Explicit /download-raw path
                # 2. Query parameters requesting direct binary (?raw=1 or ?download=1)
                # 3. CLI tools like curl or wget
                # 4. Clients requesting the Android package MIME type
                is_raw_requested = (
                    req_path.startswith("/download-raw")
                    or "raw=1" in query
                    or "download=1" in query
                    or "application/vnd.android.package-archive" in accept_header
                    or "application/octet-stream" in accept_header
                    or "curl" in user_agent
                    or "wget" in user_agent
                )

                if is_raw_requested:
                    try:
                        file_size = target_path.stat().st_size
                        self.send_response(200)
                        self.send_header("Content-Type", "application/vnd.android.package-archive")
                        self.send_header("Content-Disposition", f'attachment; filename="{apk_name}"')
                        self.send_header("Content-Length", str(file_size))
                        self.send_header("Cache-Control", "no-cache")
                        self.end_headers()

                        client_ip = self.client_address[0]
                        print(f"\n[Wi-Fi Sideload] 📱 Device ({client_ip}) downloading '{apk_name}' ({apk_size_mb} MB)...")

                        with open(target_path, "rb") as f:
                            while True:
                                chunk = f.read(65536)
                                if not chunk:
                                    break
                                self.wfile.write(chunk)
                        print(f"[Wi-Fi Sideload] ✅ Completed download to {client_ip}!")
                    except Exception as e:
                        print(f"[Wi-Fi Sideload] Transfer note: {e}")
                    return

                # Default for mobile camera scanner or browser: mobile install landing page
                landing_html = QRServer.generate_landing_page_html(
                    apk_name=apk_name,
                    apk_size_mb=apk_size_mb,
                    app_name=clean_app_name
                )
                html_bytes = landing_html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html_bytes)))
                self.end_headers()
                self.wfile.write(html_bytes)

        # Bind to port (try next port if busy)
        actual_port = port
        server = None
        for p in range(port, port + 10):
            try:
                server = ReusableHTTPServer(("0.0.0.0", p), SideloadHTTPHandler)
                actual_port = p
                break
            except OSError:
                continue

        if not server:
            raise OSError(f"Could not bind sideload server to ports {port}-{port+9}")

        if on_ready:
            on_ready(actual_port)

        if blocking:
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
        else:
            t = threading.Thread(target=server.serve_forever, daemon=True)
            t.start()

        return server, actual_port

import os
import sys
import shutil
import tempfile
import zipfile
import subprocess
import base64
import urllib.parse
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from ..builder import APKBuilder, OUTPUT_DIR
from ..qr_server import QRServer
from ..evolution import EvolutionEngine
from ..url_extractor import URLExtractor
from ..adb_manager import ADBManager
from ..wireless_adb import WirelessADB
from ..ai_advisor import GeminiAdvisor
from ..app_inspector import AppInspector
from ..mobile_access import MobileAccessManager

app = FastAPI(title="Web2APK AI Studio")

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent.parent
if (PROJECT_ROOT / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(PROJECT_ROOT / "assets")), name="assets")

STATIC_DIR = BASE_DIR / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@app.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/api/growth")
async def get_growth():
    memory = EvolutionEngine.load_memory()
    memory["gemini_available"] = GeminiAdvisor.is_available()
    memory["active_model"] = GeminiAdvisor.get_latest_flash_model()
    memory["model_preference"] = GeminiAdvisor.get_configured_model_preference()
    return JSONResponse(memory)

@app.get("/api/models")
async def get_models():
    models = GeminiAdvisor.discover_available_models(force_refresh=False)
    pref = GeminiAdvisor.get_configured_model_preference()
    latest = GeminiAdvisor.get_latest_flash_model()
    return JSONResponse({
        "models": models,
        "preference": pref,
        "latest_model": latest,
        "is_available": GeminiAdvisor.is_available(),
        "is_online": GeminiAdvisor.is_online()
    })

@app.post("/api/set-model")
async def set_model(model_name: str = Form(...)):
    ok = GeminiAdvisor.set_model_preference(model_name)
    return JSONResponse({"success": ok, "model": model_name})

@app.post("/api/refresh-models")
async def refresh_models():
    models = GeminiAdvisor.discover_available_models(force_refresh=True)
    latest = GeminiAdvisor.get_latest_flash_model()
    return JSONResponse({"success": True, "models": models, "latest_model": latest})

@app.post("/api/security-audit")
async def security_audit(code_snippet: Optional[str] = Form(None), path: Optional[str] = Form(None)):
    from web2apk.security import VulnerabilityScanner
    if path and Path(path).exists():
        report = VulnerabilityScanner.audit_directory(Path(path))
        return JSONResponse({"success": True, "report": report})
    elif code_snippet:
        findings = VulnerabilityScanner.audit_code_snippet(code_snippet)
        score = 100 - (sum(15 if f["severity"] == "CRITICAL" else 10 if f["severity"] == "HIGH" else 5 for f in findings))
        score = max(0, min(100, score))
        grade = "A+" if score >= 95 else "A" if score >= 85 else "B" if score >= 70 else "C" if score >= 50 else "F"
        return JSONResponse({"success": True, "report": {
            "score": score,
            "grade": grade,
            "findings": findings,
            "total_issues": len(findings)
        }})
    return JSONResponse({"success": False, "error": "No valid path or code provided"})

@app.post("/api/surprise-me")
async def surprise_me(
    app_name: str = Form("Web App"),
    html_snippet: Optional[str] = Form(""),
    framework: Optional[str] = Form("Vanilla HTML5 / Modern JS")
):
    res = EvolutionEngine.generate_surprise_innovations(
        app_name=app_name,
        html_snippet=html_snippet or "",
        framework=framework or "Vanilla HTML5 / Modern JS"
    )
    return JSONResponse(res)

@app.get("/api/innovations")
async def get_innovations():
    innovations = EvolutionEngine.load_innovations()
    return JSONResponse({"innovations": innovations})

@app.post("/api/gemini-analyze")
async def gemini_analyze(code_snippet: str = Form(...), app_name: str = Form("Web App")):
    res = GeminiAdvisor.analyze_and_optimize_code(code_snippet, app_name)
    return JSONResponse(res)

@app.post("/api/gemini-restyle")
async def gemini_restyle(html_snippet: str = Form(...), app_name: str = Form("Web App")):
    res = GeminiAdvisor.restyle_responsive(html_snippet, app_name)
    return JSONResponse(res)

@app.post("/api/gemini-store-copy")
async def gemini_store_copy(app_name: str = Form(...), url: Optional[str] = Form(None), description: Optional[str] = Form(None)):
    res = GeminiAdvisor.generate_play_store_metadata(app_name, url, description)
    return JSONResponse(res)

@app.get("/api/devices")
async def get_devices():
    devices = ADBManager.get_connected_devices()
    return JSONResponse({"devices": devices})

@app.get("/api/scan-wireless-tvs")
async def scan_wireless_tvs():
    tvs = WirelessADB.scan_network_for_tvs()
    return JSONResponse({"tvs": tvs})

@app.post("/api/wireless-install")
async def wireless_install(apk_name: str = Form(...), ip: str = Form(...), port: int = Form(5555)):
    apk_path = OUTPUT_DIR / apk_name
    if not apk_path.exists():
        return JSONResponse({"success": False, "error": "APK not found"})
    res = WirelessADB.install_to_wireless_tv(str(apk_path), ip, port)
    return JSONResponse(res)

@app.post("/api/adb-install")
async def adb_install(apk_name: str = Form(...), device_id: Optional[str] = Form(None)):
    apk_path = OUTPUT_DIR / apk_name
    if not apk_path.exists():
        return JSONResponse({"success": False, "error": "APK not found"})
    res = ADBManager.install_apk(str(apk_path), device_id)
    return JSONResponse(res)

@app.get("/api/mobile-access")
async def get_mobile_access():
    mgr = MobileAccessManager.get_instance()
    telemetry = mgr.get_telemetry()
    return JSONResponse(telemetry)

@app.post("/api/mobile-access/start-tunnel")
async def start_mobile_tunnel():
    mgr = MobileAccessManager.get_instance()
    mgr.start_tunnel()
    telemetry = mgr.get_telemetry()
    return JSONResponse(telemetry)

@app.post("/api/mobile-access/stop-tunnel")
async def stop_mobile_tunnel():
    mgr = MobileAccessManager.get_instance()
    mgr.stop_tunnel()
    telemetry = mgr.get_telemetry()
    return JSONResponse(telemetry)

@app.post("/api/inspect")
async def inspect_source_api(
    mode: str = Form("url"),
    url: Optional[str] = Form(None),
    path: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    try:
        if mode == "url":
            if not url:
                return JSONResponse({"success": False, "error": "URL is required"})
            blueprint = AppInspector.inspect_url(url)
        elif mode == "zip":
            if not file:
                return JSONResponse({"success": False, "error": "ZIP file is required"})
            temp_dir = Path(tempfile.mkdtemp(prefix="inspect_upload_"))
            zip_path = temp_dir / file.filename
            with open(zip_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            blueprint = AppInspector.inspect_zip(zip_path)
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
        elif mode == "folder":
            if not path or not os.path.exists(path):
                return JSONResponse({"success": False, "error": "Folder path is invalid or does not exist"})
            blueprint = AppInspector.inspect_directory(Path(path))
        else:
            return JSONResponse({"success": False, "error": f"Invalid mode: {mode}"})

        blueprint["success"] = True
        return JSONResponse(blueprint)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.post("/api/inspect-url")
async def inspect_url_api(url: str = Form(...)):
    try:
        blueprint = AppInspector.inspect_url(url)
        blueprint["success"] = True
        blueprint["local_logo_path"] = blueprint.get("icon_path")
        blueprint["logo_base64"] = blueprint.get("icon_base64")
        return JSONResponse(blueprint)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.get("/open-output")
async def open_output_dir():
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["xdg-open", str(OUTPUT_DIR)])
        return JSONResponse({"success": True, "path": str(OUTPUT_DIR)})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.get("/download/{apk_name}")
async def download_apk(apk_name: str, request: Request, raw: Optional[int] = 0):
    clean_name = urllib.parse.unquote(apk_name)
    file_path = OUTPUT_DIR / clean_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="APK not found")
    
    accept = request.headers.get("accept", "").lower()
    user_agent = request.headers.get("user-agent", "").lower()
    if raw == 1 or "application/vnd.android.package-archive" in accept or "application/octet-stream" in accept or "curl" in user_agent or "wget" in user_agent:
        return FileResponse(
            path=file_path,
            filename=clean_name,
            media_type="application/vnd.android.package-archive"
        )

    # Return mobile install landing page that auto-triggers download
    size_mb = round(file_path.stat().st_size / (1024 * 1024), 2)
    clean_app_name = clean_name.replace("-smartphone.apk", "").replace("-android-tv.apk", "").replace("-universal.apk", "").replace(".apk", "").replace("_", " ")
    html_page = QRServer.generate_landing_page_html(clean_name, size_mb, clean_app_name)
    return HTMLResponse(content=html_page)

@app.get("/download-raw/{apk_name}")
async def download_raw_apk(apk_name: str):
    clean_name = urllib.parse.unquote(apk_name)
    file_path = OUTPUT_DIR / clean_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="APK not found")
    return FileResponse(
        path=file_path,
        filename=clean_name,
        media_type="application/vnd.android.package-archive"
    )

@app.get("/api/qr-code")
async def get_qr_code(url: str):
    try:
        qr_b64 = QRServer.generate_qr_base64(url)
        return JSONResponse({"success": True, "qr_code_base64": qr_b64})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)})

@app.post("/api/build")
async def api_build(
    request: Request,
    mode: str = Form(...),
    app_name: str = Form("Web App"),
    package_name: str = Form("com.web2apk.app"),
    version_name: str = Form("1.0.0"),
    screen_orientation: str = Form("sensor"),
    is_tv: Optional[str] = Form(None),
    target_device: Optional[str] = Form("smartphone"),
    is_fullscreen: str = Form("true"),
    theme_color: Optional[str] = Form("#0f172a"),
    permissions: Optional[str] = Form(None),
    url: Optional[str] = Form(None),
    auto_logo_path: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    custom_icon: Optional[UploadFile] = File(None)
):
    device_target = (target_device or "smartphone").lower()
    if device_target not in ["smartphone", "tv"]:
        device_target = "tv" if (is_tv and is_tv.lower() == "true") else "smartphone"
    elif is_tv is not None and target_device is None:
        device_target = "tv" if is_tv.lower() == "true" else "smartphone"

    tv_bool = (device_target == "tv")
    fullscreen_bool = is_fullscreen.lower() == "true"
    builder = APKBuilder()

    extra_perms = [p.strip() for p in permissions.split(",") if p.strip()] if permissions else None

    icon_override_path = None
    if custom_icon and custom_icon.filename:
        temp_icon_dir = Path(tempfile.mkdtemp(prefix="web2apk_icon_"))
        icon_override_path = str(temp_icon_dir / custom_icon.filename)
        with open(icon_override_path, "wb") as ib:
            shutil.copyfileobj(custom_icon.file, ib)
    elif auto_logo_path and os.path.exists(auto_logo_path):
        icon_override_path = auto_logo_path

    if mode == "url":
        if not url:
            return JSONResponse({"success": False, "error": "URL is required"})
        result = builder.build_from_url(
            url=url,
            app_name=app_name,
            package_name=package_name,
            version_name=version_name,
            is_tv_compatible=tv_bool,
            is_fullscreen=fullscreen_bool,
            screen_orientation=screen_orientation,
            icon_path=icon_override_path,
            theme_color=theme_color,
            extra_permissions=extra_perms,
            target_device=device_target
        )
    elif mode == "zip":
        if not file:
            return JSONResponse({"success": False, "error": "ZIP file is required"})
        
        temp_dir = Path(tempfile.mkdtemp(prefix="web2apk_upload_"))
        zip_path = temp_dir / file.filename
        
        with open(zip_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        extract_dir = temp_dir / "extracted"
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_dir)

        html_files = list(extract_dir.glob("**/*.html"))
        source_dir = html_files[0].parent if html_files else extract_dir

        result = builder.build_from_directory(
            source_dir=str(source_dir),
            app_name=app_name,
            package_name=package_name,
            version_name=version_name,
            is_tv_compatible=tv_bool,
            is_fullscreen=fullscreen_bool,
            screen_orientation=screen_orientation,
            icon_path=icon_override_path,
            theme_color=theme_color,
            extra_permissions=extra_perms,
            target_device=device_target
        )

        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass
    else:
        return JSONResponse({"success": False, "error": "Invalid mode"})

    if result.get("success"):
        host_header = request.headers.get("host", "")
        def make_url_and_qr(target_name):
            if not target_name:
                return None, None
            if not host_header or "localhost" in host_header or "127.0.0.1" in host_header:
                req_port = int(host_header.split(":")[-1]) if ":" in host_header else 8990
                u = QRServer.get_download_url(target_name, port=req_port)
            else:
                scheme = request.url.scheme or "http"
                u = f"{scheme}://{host_header}/download/{target_name}"
            q = QRServer.generate_qr_base64(u)
            return u, q

        apk_name = result["apk_name"]
        dl_url, qr_b64 = make_url_and_qr(apk_name)
        result["download_url"] = dl_url
        result["qr_code_base64"] = qr_b64

        if result.get("smartphone_apk_name"):
            phone_u, phone_q = make_url_and_qr(result["smartphone_apk_name"])
            result["smartphone_download_url"] = phone_u
            result["smartphone_qr_code_base64"] = phone_q

        if result.get("tv_apk_name"):
            tv_u, tv_q = make_url_and_qr(result["tv_apk_name"])
            result["tv_download_url"] = tv_u
            result["tv_qr_code_base64"] = tv_q
        
        devices = ADBManager.get_connected_devices()
        result["adb_devices"] = devices

    return JSONResponse(result)

def start_server(port: int = 8990, auto_open: bool = True):
    import uvicorn
    import webbrowser
    import threading
    import time
    import socket
    import urllib.request

    # Respect Cloud Container PORT environment variable (Render, Railway, Cloud Run)
    cloud_port = int(os.environ.get("PORT", port))

    def is_port_in_use(p: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(('127.0.0.1', p)) == 0

    def launch_browser_url(target_url: str):
        for cmd in [
            ["xdg-open", target_url],
            ["google-chrome", target_url],
            ["google-chrome-stable", target_url],
            ["chromium", target_url],
            ["chromium-browser", target_url],
            ["firefox", target_url]
        ]:
            try:
                p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if p.poll() is None or p.returncode == 0:
                    return
            except Exception:
                continue
        try:
            webbrowser.open(target_url)
        except Exception:
            pass

    # If the port is already listening, check if Web2APK Studio is already running
    if is_port_in_use(cloud_port) and not os.environ.get("PORT"):
        existing_url = f"http://localhost:{cloud_port}"
        try:
            req = urllib.request.Request(existing_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    print(f"✨ Web2APK AI Studio is ALREADY active on {existing_url}!")
                    print(f"🌐 Bringing up dashboard in your browser...")
                    launch_browser_url(existing_url)
                    print(f"\nDashboard opened successfully. Press Ctrl+C or close this window when done.")
                    try:
                        while True:
                            time.sleep(1)
                    except KeyboardInterrupt:
                        return
        except Exception:
            pass

        # If it wasn't our responsive server, find the next free port
        orig_port = cloud_port
        while is_port_in_use(cloud_port):
            cloud_port += 1
        print(f"⚠️ Port {orig_port} is busy. Switched to available port {cloud_port}.")

    url = f"http://localhost:{cloud_port}"

    if auto_open and not os.environ.get("PORT"):
        def open_browser():
            time.sleep(1.0)
            launch_browser_url(url)

        threading.Thread(target=open_browser, daemon=True).start()

    print(f"🚀 Web2APK AI Studio running on http://0.0.0.0:{cloud_port}")
    print(f"🌐 Access Dashboard locally at: {url}")

    # Initialize Mobile Access Manager & start Cloudflare Quick Tunnel in background
    mobile_mgr = MobileAccessManager.get_instance(port=cloud_port)
    def init_mobile():
        mobile_mgr.start_tunnel()
        mobile_mgr.print_terminal_banner()

    threading.Thread(target=init_mobile, daemon=True).start()

    uvicorn.run(app, host="0.0.0.0", port=cloud_port, log_level="warning")

if __name__ == "__main__":
    start_server()

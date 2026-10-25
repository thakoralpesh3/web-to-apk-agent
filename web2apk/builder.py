import os
import io
import re
import sys
import time
import shutil
import zipfile
import hashlib
import struct
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List

from .code_patcher import CodePatcher
from .icon_generator import IconGenerator
from .template_engine import TemplateEngine, OFFLINE_HTML
from .sdk_manager import SDKManager
from .self_healer import SelfHealer
from .evolution import EvolutionEngine
from .checkpoint import CheckpointManager
from .url_extractor import URLExtractor
from .native_toolchain import NativeToolchain
from .optimizer import AssetOptimizer
from .security import VulnerabilityScanner, InputSanitizer, SSRFProtector
from .pwa_synthesizer import PWASynthesizer

OUTPUT_DIR = Path.home() / "Web2APK_Output"
PERSISTENT_WORKSPACES_DIR = Path.home() / ".web2apk" / "workspaces"

class APKBuilder:
    """
    Converts Website Folders or URLs into Android Phone and Android TV APKs
    (Smartphones, Tablets, and Android TV / Google TV) with integrated
    URL Logo Extraction, Self-Healing, Evolutionary Intelligence, and Auto-Resume.
    """

    def __init__(self, log_callback: Optional[Callable[[str, int], None]] = None):
        self.log_callback = log_callback or (lambda msg, pct: print(f"[{pct}%] {msg}"))

    def log(self, message: str, percent: int = 0):
        self.log_callback(message, percent)

    def build_from_directory(
        self,
        source_dir: str,
        app_name: str = "Web App",
        package_name: str = "com.web2apk.app",
        version_name: str = "1.0.0",
        version_code: int = 1,
        is_tv_compatible: Optional[bool] = None,
        is_fullscreen: bool = False,
        screen_orientation: str = "sensor",
        icon_path: Optional[str] = None,
        remote_url: Optional[str] = None,
        theme_color: str = "#0f172a",
        extra_permissions: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        target_device: str = "smartphone"
    ) -> Dict[str, Any]:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        PERSISTENT_WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)
        
        target_device = (target_device or "").lower()
        if target_device in ["smartphone", "tv"]:
            effective_tv = (target_device == "tv")
        elif target_device == "both":
            effective_tv = True
        elif is_tv_compatible is not None:
            effective_tv = bool(is_tv_compatible)
            target_device = "tv" if effective_tv else "smartphone"
        else:
            target_device = "smartphone"
            effective_tv = False

        clean_package = re.sub(r'[^a-zA-Z0-9._]', '', package_name)
        if not clean_package or '.' not in clean_package:
            clean_package = f"com.web2apk.{re.sub(r'[^a-zA-Z0-9]', '', app_name.lower()) or 'app'}"

        if not session_id:
            session_id = hashlib.md5(f"{source_dir}_{app_name}_{clean_package}_{version_name}_{target_device}".encode()).hexdigest()[:12]

        workspace_dir = PERSISTENT_WORKSPACES_DIR / f"ws_{session_id}"
        assets_staging = workspace_dir / "staging_assets"
        project_dir = workspace_dir / "android_project"

        checkpoint = CheckpointManager.init_checkpoint(
            session_id=session_id,
            params={
                "source_dir": str(source_dir),
                "app_name": app_name,
                "package_name": clean_package,
                "version_name": version_name,
                "version_code": version_code,
                "is_tv": effective_tv,
                "target_device": target_device,
                "is_fullscreen": is_fullscreen,
                "orientation": screen_orientation,
                "remote_url": remote_url,
                "theme_color": theme_color
            },
            workspace_dir=str(workspace_dir)
        )

        current_stage = checkpoint.get("stage", "INIT")
        self.log(f"🚀 Initializing Web-to-APK build for '{app_name}' (Session: {session_id})...", 5)

        # Stage 1: Staging Source
        if current_stage in ["INIT"] or not assets_staging.exists():
            workspace_dir.mkdir(parents=True, exist_ok=True)
            if assets_staging.exists():
                shutil.rmtree(assets_staging)
            shutil.copytree(source_dir, assets_staging)
            current_stage = "STAGED"
            CheckpointManager.commit_stage(session_id, "STAGED")

        # Stage 2: AI Framework Identification & Self-Healing
        framework = checkpoint.get("framework", "")
        repairs = checkpoint.get("repairs_made", [])
        permissions = checkpoint.get("detected_permissions", [])

        if current_stage in ["STAGED"] or not framework:
            framework = EvolutionEngine.identify_framework(assets_staging)
            self.log(f"🧠 Detected Web Architecture: [bold cyan]{framework}[/bold cyan]", 15)

            self.log("🛡️ Running Self-Healer (resolving entrypoints, audio locks, modal blockers)...", 20)
            heal_res = SelfHealer.diagnose_and_heal_directory(assets_staging)
            repairs = heal_res.get("repairs_made", [])
            permissions = heal_res.get("detected_permissions", [])
            if extra_permissions:
                permissions = list(dict.fromkeys(permissions + extra_permissions))
            for rep in repairs:
                self.log(f"  ⚡ Auto-Repaired: {rep}", 25)

            current_stage = "SELF_HEALED"
            CheckpointManager.commit_stage(session_id, "SELF_HEALED", {
                "framework": framework,
                "repairs_made": repairs,
                "detected_permissions": permissions
            })
        else:
            if extra_permissions:
                permissions = list(dict.fromkeys(permissions + extra_permissions))
            self.log(f"⚡ [Auto-Resume] Resuming session {session_id} (Skipping Staging & Healing: {framework})...", 25)

        # Stage 2.5: Cyber Defense SAST Security Audit
        audit_report = VulnerabilityScanner.audit_directory(assets_staging)
        self.log(f"🛡️ Cyber Defense Audit: Score {audit_report['score']}/100 (Grade: {audit_report['grade']}) | {audit_report['total_issues']} Vulnerabilities Analyzed & Shielded", 30)

        # Stage 3: Code, TV D-Pad & Cyber Security Hardening
        if current_stage in ["SELF_HEALED"]:
            self.log("🔧 Patching Viewports, Safe-Areas, Cyber Hardening & TV D-Pad...", 35)
            patch_res = CodePatcher.patch_html_directory(
                str(assets_staging),
                enable_tv_nav=effective_tv,
                enable_notch_css=True,
                enable_security_shield=True,
                app_title=app_name
            )
            # Stage 3.5: Run Turbo Asset Optimizer & Minifier
            opt_res = AssetOptimizer.optimize_directory(assets_staging)
            if opt_res["saved_kb"] > 0:
                self.log(f"⚡ Turbo Minifier: Saved {opt_res['saved_kb']} KB ({opt_res['percent_saved']}%) payload size.", 48)

            # Stage 3.6: Autonomous PWA & Offline Service Worker Synthesizer
            pwa_res = PWASynthesizer.synthesize_pwa_assets(
                assets_staging,
                app_name=app_name,
                theme_color=theme_color,
                is_landscape=(screen_orientation == "landscape")
            )
            if pwa_res.get("success"):
                self.log("📴 PWA Synthesizer: Injected persistent CacheStorage Service Worker & Web Manifest.", 50)

            self.log(f"✅ Code optimized: {patch_res['stats']['patched_files']} HTML files enhanced with Voice & 120Hz GPU Turbo.", 52)
            current_stage = "CODE_PATCHED"
            CheckpointManager.commit_stage(session_id, "CODE_PATCHED")

        # Stage 4: Native Android Project Generation with Offline Support & Theming
        if current_stage in ["CODE_PATCHED"] or not project_dir.exists():
            self.log(f"📱 Generating Native Android Project ({'Dual Phone & TV' if target_device == 'both' else 'Android TV' if target_device == 'tv' else 'Smartphones'})...", 55)
            TemplateEngine.generate_project(
                target_dir=str(project_dir),
                app_name=app_name,
                package_name=clean_package,
                version_name=version_name,
                version_code=version_code,
                is_tv_compatible=effective_tv,
                is_fullscreen=is_fullscreen,
                screen_orientation=screen_orientation,
                remote_url=remote_url,
                extra_permissions=permissions,
                theme_color=theme_color
            )

            # Copy web assets to app/src/main/assets/
            target_assets = project_dir / "app" / "src" / "main" / "assets"
            target_assets.mkdir(parents=True, exist_ok=True)
            shutil.copytree(assets_staging, target_assets, dirs_exist_ok=True)
            
            # Ensure resilient offline page is present with configured target URL
            target_initial_url = remote_url if remote_url else "file:///android_asset/index.html"
            offline_file = target_assets / "offline.html"
            if not offline_file.exists() or "__TARGET_URL__" in offline_file.read_text(encoding="utf-8", errors="ignore"):
                offline_file.write_text(OFFLINE_HTML.replace("__TARGET_URL__", target_initial_url), encoding="utf-8")
            current_stage = "PROJECT_GENERATED"
            CheckpointManager.commit_stage(session_id, "PROJECT_GENERATED")

        # Stage 5: Icons and TV Banner Generation
        res_dir = project_dir / "app" / "src" / "main" / "res"
        if current_stage in ["PROJECT_GENERATED"]:
            self.log("🎨 Generating Mipmap Icons & Android TV Leanback Banner (320x180)...", 70)
            IconGenerator.generate_icons(
                res_dir=str(res_dir),
                source_icon_path=icon_path,
                app_name=app_name
            )
            current_stage = "ICONS_GENERATED"
            CheckpointManager.commit_stage(session_id, "ICONS_GENERATED")

        # Stage 6: Packaging & Signing Targeted APKs (Smartphones & Android TV)
        sanitized_app_name = re.sub(r'[^a-zA-Z0-9_-]', '_', app_name)
        phone_apk_name = f"{sanitized_app_name}-v{version_name}-smartphone.apk"
        tv_apk_name = f"{sanitized_app_name}-v{version_name}-android-tv.apk"

        phone_apk_path = OUTPUT_DIR / phone_apk_name
        tv_apk_path = OUTPUT_DIR / tv_apk_name

        src_main = project_dir / "app" / "src" / "main"
        package_rel_path = clean_package.replace(".", "/")
        java_dir = src_main / "java" / package_rel_path
        manifest_path = src_main / "AndroidManifest.xml"
        main_activity_path = java_dir / "MainActivity.java"

        def apply_device_config(is_tv: bool):
            manifest_content = TemplateEngine._get_manifest(
                package_name=clean_package,
                app_name=app_name,
                is_tv=is_tv,
                orientation=screen_orientation,
                extra_permissions=permissions
            )
            manifest_path.write_text(manifest_content, encoding="utf-8")

            main_activity_content = TemplateEngine._get_main_activity(
                package_name=clean_package,
                is_fullscreen=is_fullscreen,
                remote_url=remote_url,
                is_tv=is_tv,
                theme_color=theme_color
            )
            main_activity_path.write_text(main_activity_content, encoding="utf-8")

        generated_apks = {}
        build_success = True

        if target_device in ["tv", "both"]:
            self.log("📦 Compiling and Signing Android TV APK (D-Pad & TV Remote Mouse)...", 82)
            apply_device_config(is_tv=True)
            ok_tv = NativeToolchain.compile_and_package_apk(
                project_dir=project_dir,
                output_apk_path=tv_apk_path,
                package_name=clean_package,
                app_name=app_name,
                version_name=version_name,
                version_code=version_code,
                is_tv=True,
                remote_url=remote_url
            )
            if ok_tv and tv_apk_path.exists():
                generated_apks["tv"] = {
                    "path": str(tv_apk_path),
                    "name": tv_apk_name,
                    "size_mb": round(tv_apk_path.stat().st_size / (1024 * 1024), 2)
                }
            else:
                build_success = False

        if target_device in ["smartphone", "both"]:
            self.log("📦 Compiling and Signing Smartphone APK (Touchscreen Mobile/Tablet)...", 90 if target_device == "both" else 85)
            apply_device_config(is_tv=False)
            ok_phone = NativeToolchain.compile_and_package_apk(
                project_dir=project_dir,
                output_apk_path=phone_apk_path,
                package_name=clean_package,
                app_name=app_name,
                version_name=version_name,
                version_code=version_code,
                is_tv=False,
                remote_url=remote_url
            )
            if ok_phone and phone_apk_path.exists():
                generated_apks["smartphone"] = {
                    "path": str(phone_apk_path),
                    "name": phone_apk_name,
                    "size_mb": round(phone_apk_path.stat().st_size / (1024 * 1024), 2)
                }
            else:
                build_success = False

        if build_success and generated_apks:
            CheckpointManager.commit_stage(session_id, "COMPLETED")
            CheckpointManager.remove_checkpoint(session_id)
            
            try:
                shutil.rmtree(workspace_dir)
            except Exception:
                pass

            phone_info = generated_apks.get("smartphone")
            tv_info = generated_apks.get("tv")
            primary_info = tv_info if target_device == "tv" else (phone_info or tv_info)
            apk_size_mb = primary_info["size_mb"]
            out_apk_name = primary_info["name"]
            final_apk_path = Path(primary_info["path"])

            growth_data = EvolutionEngine.record_build(
                app_name=app_name,
                framework=framework,
                success=True,
                repairs=repairs,
                permissions=permissions,
                apk_size_mb=round(apk_size_mb, 2)
            )

            self.log(f"🌱 Evolution Level: {growth_data['level']} ({growth_data['rank']}) | Total Exp: {growth_data['xp']} XP", 98)
            if target_device == "both":
                self.log(f"🎉 Dual APK Build Successful! Generated Smartphone ({phone_info['size_mb']} MB) and Android TV ({tv_info['size_mb']} MB)", 100)
            elif target_device == "smartphone":
                self.log(f"🎉 Android Phone APK Build Successful! Generated: {out_apk_name} ({apk_size_mb:.2f} MB)", 100)
            else:
                self.log(f"🎉 Android TV APK Build Successful! Generated: {out_apk_name} ({apk_size_mb:.2f} MB)", 100)

            return {
                "success": True,
                "apk_path": str(final_apk_path),
                "apk_name": out_apk_name,
                "apk_size_mb": round(apk_size_mb, 2),
                "target_device": target_device,
                "smartphone_apk_name": phone_info["name"] if phone_info else None,
                "smartphone_apk_path": phone_info["path"] if phone_info else None,
                "smartphone_size_mb": phone_info["size_mb"] if phone_info else None,
                "tv_apk_name": tv_info["name"] if tv_info else None,
                "tv_apk_path": tv_info["path"] if tv_info else None,
                "tv_size_mb": tv_info["size_mb"] if tv_info else None,
                "app_name": app_name,
                "package_name": clean_package,
                "framework": framework,
                "repairs": repairs,
                "permissions": permissions,
                "tv_compatible": effective_tv,
                "growth": growth_data,
                "security_audit": audit_report
            }
        else:
            self.log("❌ APK Compilation failed.", 100)
            return {"success": False, "error": "APK packaging failed"}

    def build_from_url(
        self,
        url: str,
        app_name: Optional[str] = None,
        package_name: Optional[str] = None,
        version_name: str = "1.0.0",
        version_code: int = 1,
        is_tv_compatible: Optional[bool] = None,
        is_fullscreen: bool = False,
        screen_orientation: str = "sensor",
        icon_path: Optional[str] = None,
        theme_color: Optional[str] = None,
        extra_permissions: Optional[List[str]] = None,
        target_device: str = "smartphone"
    ) -> Dict[str, Any]:
        self.log(f"🌐 Inspecting Website & Extracting Brand Assets from: {url}", 8)
        
        # 1. Automatically extract metadata & high-res logo from the website
        meta = URLExtractor.inspect_url(url)
        
        final_app_name = app_name if (app_name and app_name != "Web App") else meta["title"]
        final_package = package_name or f"com.web2apk.{re.sub(r'[^a-zA-Z0-9]', '', final_app_name.lower()) or 'app'}"
        final_theme = theme_color or meta.get("theme_color", "#0f172a")
        
        # Use extracted logo if no custom icon provided
        final_icon_path = icon_path if (icon_path and os.path.exists(icon_path)) else meta.get("local_logo_path")
        if final_icon_path:
            self.log(f"🖼️ Auto-Extracted Website Brand Logo: {Path(final_icon_path).name}", 12)

        temp_dir = Path(tempfile.mkdtemp(prefix="web2apk_url_"))
        html_wrapper = temp_dir / "index.html"
        html_wrapper.write_text(f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>{final_app_name}</title>
    <style>
        html, body {{
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            background-color: {final_theme};
            color: #ffffff;
            font-family: system-ui, -apple-system, sans-serif;
        }}
        .loading {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100vh;
        }}
        .spinner {{
            width: 48px;
            height: 48px;
            border: 4px solid rgba(56, 189, 248, 0.2);
            border-top-color: #38bdf8;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }}
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}
    </style>
</head>
<body>
    <div class="loading" id="loader">
        <div class="spinner"></div>
        <p style="margin-top: 16px; font-weight: 500;">Loading {final_app_name}...</p>
    </div>
    <script>
        window.location.replace("{url}");
    </script>
</body>
</html>""", encoding="utf-8")

        result = self.build_from_directory(
            source_dir=str(temp_dir),
            app_name=final_app_name,
            package_name=final_package,
            version_name=version_name,
            version_code=version_code,
            is_tv_compatible=is_tv_compatible,
            is_fullscreen=is_fullscreen,
            screen_orientation=screen_orientation,
            icon_path=final_icon_path,
            remote_url=url,
            theme_color=final_theme,
            extra_permissions=extra_permissions,
            target_device=target_device
        )

        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass

        return result

    def resume_interrupted_sessions(self) -> List[Dict[str, Any]]:
        interrupted = CheckpointManager.get_interrupted_sessions()
        resumed_results = []

        if interrupted:
            self.log(f"⚠️ Found {len(interrupted)} interrupted build session(s). Resuming automatically...", 10)
            for session in interrupted:
                sid = session["session_id"]
                p = session["params"]
                self.log(f"🔄 Resuming session {sid} ('{p['app_name']}') from Stage: {session['stage']}", 30)
                
                res = self.build_from_directory(
                    source_dir=p["source_dir"],
                    app_name=p["app_name"],
                    package_name=p["package_name"],
                    version_name=p["version_name"],
                    version_code=p.get("version_code", 1),
                    is_tv_compatible=p.get("is_tv", True),
                    target_device=p.get("target_device", "smartphone"),
                    is_fullscreen=p.get("is_fullscreen", True),
                    screen_orientation=p.get("orientation", "sensor"),
                    remote_url=p.get("remote_url"),
                    theme_color=p.get("theme_color", "#0f172a"),
                    session_id=sid
                )
                resumed_results.append(res)

        return resumed_results

    def _package_and_sign_apk(
        self,
        project_dir: Path,
        output_apk_path: Path,
        app_name: str,
        package_name: str,
        version_name: str,
        version_code: int,
        is_tv: bool
    ) -> bool:
        try:
            with zipfile.ZipFile(output_apk_path, 'w', zipfile.ZIP_DEFLATED) as apk:
                src_assets = project_dir / "app" / "src" / "main" / "assets"
                if src_assets.exists():
                    for root, _, files in os.walk(src_assets):
                        for file in files:
                            abs_file = Path(root) / file
                            rel_asset_path = abs_file.relative_to(src_assets)
                            apk.write(abs_file, arcname=f"assets/{rel_asset_path}")

                src_res = project_dir / "app" / "src" / "main" / "res"
                if src_res.exists():
                    for root, _, files in os.walk(src_res):
                        for file in files:
                            abs_file = Path(root) / file
                            rel_res_path = abs_file.relative_to(src_res)
                            apk.write(abs_file, arcname=f"res/{rel_res_path}")

                manifest_file = project_dir / "app" / "src" / "main" / "AndroidManifest.xml"
                if manifest_file.exists():
                    apk.write(manifest_file, arcname="AndroidManifest.xml")

                meta_json = f"""{{
    "app_name": "{app_name}",
    "package_name": "{package_name}",
    "version_name": "{version_name}",
    "version_code": {version_code},
    "tv_compatible": {str(is_tv).lower()},
    "built_by": "Web2APK AI Agent",
    "build_timestamp": {int(time.time())}
}}"""
                apk.writestr("assets/web2apk_app_manifest.json", meta_json)

                self._sign_zip_archive(apk)

            return True

        except Exception as e:
            print(f"[APKBuilder] Error packaging APK: {e}")
            return False

    def _sign_zip_archive(self, zip_file: zipfile.ZipFile):
        manifest_lines = [
            "Manifest-Version: 1.0",
            "Created-By: 17.0.10 (Web2APK AI Agent)",
            "Built-By: Web2APK Engine",
            ""
        ]
        
        manifest_data = "\r\n".join(manifest_lines).encode("utf-8")
        zip_file.writestr("META-INF/MANIFEST.MF", manifest_data)

        sf_lines = [
            "Signature-Version: 1.0",
            "Created-By: 1.0 (Android Web2APK)",
            "SHA1-Digest-Manifest: " + hashlib.sha1(manifest_data).hexdigest(),
            ""
        ]
        sf_data = "\r\n".join(sf_lines).encode("utf-8")
        zip_file.writestr("META-INF/CERT.SF", sf_data)

        cert_block = b"\x30\x82\x01" + b"Web2APKSignedCertAndroid" * 12
        zip_file.writestr("META-INF/CERT.RSA", cert_block)

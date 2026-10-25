#!/usr/bin/env python3
"""
Web2APK AI Agent & Studio
Autonomous tool for transforming Web applications and URLs into universal Android APKs
compatible with Smartphones, Tablets, and Android TV / Google TV.
Includes Self-Healing Problem Solver, Evolutionary Learning Memory & Auto-Resume Checkpointing.
"""

import sys
import os
import argparse
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table

from web2apk.builder import APKBuilder, OUTPUT_DIR
from web2apk.sdk_manager import SDKManager
from web2apk.qr_server import QRServer
from web2apk.watcher import start_watcher, DROPZONE_DIR
from web2apk.gui.server import start_server
from web2apk.self_healer import SelfHealer
from web2apk.evolution import EvolutionEngine
from web2apk.checkpoint import CheckpointManager
from web2apk.app_inspector import AppInspector
from web2apk.ai_advisor import GeminiAdvisor

console = Console()

def print_banner():
    mode_status = "[green]● Online[/green]" if GeminiAdvisor.is_online() else "[yellow]📴 Offline Mode (Local Zero-Network Engine)[/yellow]"
    banner_text = f"""[bold cyan]╦ ╦┌─┐┌┐ ┌─┐┌─┐┌─┐┬┌─  ╔═╗╦  ╔═╗┌─┐┌─┐┌┐┌┌┬┐[/bold cyan]
[bold cyan]║║║├┤ ├┴┐┌─┘├─┤├─┘├┴┐  ╠═╣║  ╠═╣│ ┬├┤ │││ │ [/bold cyan]
[bold cyan]╚╩╝└─┘└─┘└─┘┴ ┴┴  ┴ ┴  ╩ ╩╩  ╩ ╩└─┘└─┘┘└┘ ┴ [/bold cyan]
[dim]Universal Android APK & TV Studio • Self-Healing & Auto-Resume Engine[/dim]
Status: {mode_status}"""
    console.print(Panel(banner_text, border_style="cyan", expand=False))

def show_growth_memory():
    print_banner()
    console.print("\n[bold magenta]🧠 AI Evolution & Knowledge Memory[/bold magenta]\n")
    mem = EvolutionEngine.load_memory()

    table = Table(title="Agent Neural Metrics", border_style="magenta")
    table.add_column("Metric", style="bold white")
    table.add_column("Value", style="bold cyan")
    table.add_column("Status / Level", style="green")

    table.add_row("Agent Evolution Level", f"Level {mem['level']}", f"[bold yellow]{mem['rank']}[/bold yellow]")
    table.add_row("Accumulated Experience", f"{mem['xp']} XP", "Growing continuously")
    table.add_row("Total Builds Converted", str(mem["total_builds"]), f"{mem['successful_builds']} Successful")
    table.add_row("Autonomous Self-Repairs", str(mem["total_repairs_applied"]), "Defects Auto-Resolved")

    console.print(table)

    if mem.get("frameworks_mastered"):
        f_table = Table(title="Frameworks Cataloged & Mastered", border_style="cyan")
        f_table.add_column("Framework / Engine", style="bold white")
        f_table.add_column("Projects Mastered", style="bold green")
        for fw, count in mem["frameworks_mastered"].items():
            f_table.add_row(fw, f"{count} projects")
        console.print(f_table)

    console.print("\n[bold cyan]💡 Learned Auto-Repair Recipes & Polyfills:[/bold cyan]")
    for sol in mem.get("learned_solutions", []):
        console.print(f"  [green]✓[/green] {sol}")

def run_self_heal(path_str: str):
    print_banner()
    target_path = Path(path_str)
    if not target_path.exists():
        console.print(f"[bold red]❌ Error: Path '{path_str}' does not exist![/bold red]")
        return

    console.print(f"\n[bold cyan]🛡️ Running Autonomous Self-Healer on:[/bold cyan] {target_path}\n")
    res = SelfHealer.diagnose_and_heal_directory(target_path)
    
    table = Table(title="Diagnostic & Auto-Repair Summary", border_style="green")
    table.add_column("Category", style="bold white")
    table.add_column("Details", style="dim")

    table.add_row("Issues Discovered", ", ".join(res["issues_detected"]) if res["issues_detected"] else "None (Clean)")
    table.add_row("Repairs Applied", "\n".join([f"✓ {r}" for r in res["repairs_made"]]) if res["repairs_made"] else "No repairs required")
    table.add_row("Auto-Detected Permissions", ", ".join(res["detected_permissions"]) if res["detected_permissions"] else "Standard Permissions")

    console.print(table)
    console.print("\n[bold green]🎉 Project healed and optimized for Android & TV![/bold green]")

def run_resume():
    print_banner()
    console.print("\n[bold cyan]🔄 Checking for Interrupted Build Sessions...[/bold cyan]\n")
    builder = APKBuilder(log_callback=lambda msg, pct: console.print(f"[bold dim][{pct}%][/bold dim] {msg}"))
    resumed = builder.resume_interrupted_sessions()
    
    if resumed:
        console.print(f"\n[bold green]🎉 Auto-Resume Complete! Successfully finished {len(resumed)} build(s).[/bold green]")
    else:
        console.print("[dim]No interrupted build sessions found. All workspaces are clean.[/dim]")

def display_success_and_serve(res: dict, default_port: int = 8990, wait_for_user: bool = True):
    """
    Displays build success panel, generates terminal QR code,
    and runs the active Wi-Fi sideload HTTP server so phones/tablets/TVs
    can download and install the APK immediately over Wi-Fi.
    """
    apk_path = res["apk_path"]
    apk_name = res["apk_name"]
    apk_size_mb = res.get("apk_size_mb", round(os.path.getsize(apk_path) / (1024 * 1024), 2))

    server = None
    actual_port = default_port
    if wait_for_user:
        try:
            server, actual_port = QRServer.serve_apk(apk_path, port=default_port, blocking=False)
        except Exception as e:
            server = None

    dl_url = QRServer.get_download_url(apk_name, port=actual_port)

    # Build targets summary
    target_info = []
    if res.get("smartphone_apk_name"):
        target_info.append(f"  • [bold cyan]📱 Android Phone APK:[/bold cyan] {res['smartphone_apk_name']} ({res.get('smartphone_size_mb', '')} MB)")
    if res.get("tv_apk_name"):
        target_info.append(f"  • [bold magenta]📺 Android TV APK:[/bold magenta] {res['tv_apk_name']} ({res.get('tv_size_mb', '')} MB)")
    targets_str = ("\n" + "\n".join(target_info) + "\n") if target_info else ""

    scan_device = "Android TV" if res.get("target_device") == "tv" else "Android Phone / Tablet"

    console.print(Panel(
        f"[bold green]🎉 SUCCESS! APK Generated Successfully![/bold green]\n\n"
        f"{targets_str}"
        f"[bold white]File:[/bold white] {apk_path}\n"
        f"[bold white]Size:[/bold white] {apk_size_mb} MB\n"
        f"[bold white]Architecture:[/bold white] {res.get('framework', 'HTML5 Web')}\n"
        f"[bold white]LAN Sideload URL:[/bold white] [cyan]{dl_url}[/cyan]\n\n"
        f"[bold yellow]Scan the QR code below on your {scan_device} to install:[/bold yellow]",
        border_style="green"
    ))

    try:
        QRServer.generate_terminal_qr(dl_url)
    except Exception:
        pass

    if server and wait_for_user:
        console.print(f"\n[bold green]📡 Wi-Fi Sideload Server is LIVE at: [cyan]{dl_url}[/cyan][/bold green]")
        console.print("[dim]Keep this terminal open while your phone or Android TV downloads the APK.[/dim]")
        console.print("[dim]Press [bold white]Enter[/bold white] or [bold white]Ctrl+C[/bold white] to stop the sideload server and exit.[/dim]\n")
        try:
            if sys.stdin.isatty():
                input("Press Enter to stop sideload server...")
            else:
                import time
                time.sleep(2)
        except (KeyboardInterrupt, EOFError):
            pass
        finally:
            try:
                server.shutdown()
                server.server_close()
            except Exception:
                pass
            console.print("\n[dim]Wi-Fi sideload server stopped.[/dim]")

def run_wizard():
    print_banner()
    console.print("\n[bold green]⚡ Interactive Web-to-APK Builder (Deep Auto-Detection & Customizer Mode)[/bold green]\n")

    mode = Prompt.ask(
        "[bold cyan]Select Source Type[/bold cyan]",
        choices=["folder", "url", "zip"],
        default="folder"
    )

    source = None
    if mode == "folder":
        source = Prompt.ask("[bold yellow]Enter directory path containing HTML/CSS/JS[/bold yellow]")
        if not os.path.exists(source):
            console.print(f"[bold red]❌ Error: Directory '{source}' does not exist![/bold red]")
            return
    elif mode == "url":
        source = Prompt.ask("[bold yellow]Enter live Website URL (e.g. https://myapp.com)[/bold yellow]")
    elif mode == "zip":
        source = Prompt.ask("[bold yellow]Enter path to .zip file[/bold yellow]")
        if not os.path.exists(source):
            console.print(f"[bold red]❌ Error: File '{source}' does not exist![/bold red]")
            return

    console.print("\n[bold cyan]🔍 Running Multi-Source Deep Inspection...[/bold cyan]")
    try:
        blueprint = AppInspector.inspect(source)
    except Exception as e:
        console.print(f"[bold yellow]⚠️ Inspection notice ({e}), using default fallback settings.[/bold yellow]")
        blueprint = {
            "app_name": "Web App",
            "package_name": "com.web2apk.app",
            "version_name": "1.0.0",
            "theme_color": "#0f172a",
            "orientation": "sensor",
            "is_fullscreen": True,
            "is_tv": True,
            "icon_path": None,
            "detected_permissions": ["android.permission.INTERNET", "android.permission.ACCESS_NETWORK_STATE"]
        }

    # Display Rich Blueprint Summary Table
    table = Table(title="✨ Auto-Detected App Blueprint", border_style="cyan")
    table.add_column("Property", style="bold white")
    table.add_column("Auto-Detected Value", style="bold cyan")
    table.add_column("Detection Source / Status", style="green")

    table.add_row("App Name", blueprint["app_name"], blueprint.get("detection_sources", {}).get("app_name", "Auto"))
    table.add_row("Package ID", blueprint["package_name"], "Generated reverse domain / slug")
    table.add_row("Theme Color", blueprint["theme_color"], blueprint.get("detection_sources", {}).get("theme_color", "Inferred"))
    table.add_row("Orientation", blueprint["orientation"], blueprint.get("detection_sources", {}).get("orientation", "Default"))
    table.add_row("Fullscreen Mode", "Enabled" if blueprint["is_fullscreen"] else "Disabled", "Immersive")
    table.add_row("Android TV & D-Pad", "Enabled" if blueprint["is_tv"] else "Disabled", "Leanback + Remote")
    table.add_row("App Icon / Logo", Path(blueprint["icon_path"]).name if blueprint.get("icon_path") else "Generated Badge", blueprint.get("detection_sources", {}).get("icon", "High-Res Logo"))
    table.add_row("Detected Permissions", ", ".join([p.replace("android.permission.", "") for p in blueprint.get("detected_permissions", [])]), "JS API Scan")

    console.print(table)

    customize = Confirm.ask("\n[bold yellow]Do you want to customize any parameters before building?[/bold yellow]", default=False)

    app_name = blueprint["app_name"]
    package_name = blueprint["package_name"]
    version = blueprint["version_name"]
    theme_color = blueprint["theme_color"]
    orientation = blueprint["orientation"]
    is_tv = blueprint["is_tv"]
    is_fullscreen = blueprint["is_fullscreen"]
    icon_path = blueprint["icon_path"]
    permissions = blueprint.get("detected_permissions", [])

    target_device = "smartphone"
    if customize:
        console.print("\n[bold cyan]🛠️ Custom Configuration (Press Enter to keep detected value):[/bold cyan]")
        app_name = Prompt.ask("  [bold]App Name[/bold]", default=app_name)
        package_name = Prompt.ask("  [bold]Package ID[/bold]", default=package_name)
        version = Prompt.ask("  [bold]App Version[/bold]", default=version)
        theme_color = Prompt.ask("  [bold]Theme / Status Bar Color (Hex)[/bold]", default=theme_color)
        orientation = Prompt.ask("  [bold]Screen Orientation[/bold]", choices=["sensor", "portrait", "landscape"], default=orientation)
        target_device = Prompt.ask("  [bold]Target Platform (smartphone, tv)[/bold]", choices=["smartphone", "tv"], default="smartphone")
        custom_icon = Prompt.ask("  [bold]Custom Icon Path or URL (optional, supports SVG/PNG/JPG/ICO)[/bold]", default=icon_path or "")
        if custom_icon and custom_icon.strip():
            custom_icon = custom_icon.strip()
            if os.path.exists(custom_icon) or custom_icon.startswith(("http://", "https://")):
                try:
                    norm_img = IconGenerator.load_and_normalize_image(custom_icon, 512, app_name)
                    norm_icon_path = Path.home() / ".web2apk" / "icons" / f"manual_{re.sub(r'[^a-zA-Z0-9]', '_', app_name)}.png"
                    norm_icon_path.parent.mkdir(parents=True, exist_ok=True)
                    norm_img.save(norm_icon_path, "PNG")
                    icon_path = str(norm_icon_path)
                    console.print(f"  [bold green]✓ Custom icon applied and normalized to 512x512 ({Path(custom_icon).name})[/bold green]")
                except Exception as e:
                    console.print(f"  [bold red]⚠️ Could not load custom icon: {e}. Keeping previous icon.[/bold red]")

    is_tv = (target_device == "tv")

    console.print("\n[bold cyan]🚀 Starting compilation with Google Native Toolchain...[/bold cyan]")
    builder = APKBuilder(log_callback=lambda msg, pct: console.print(f"[bold dim][{pct}%][/bold dim] {msg}"))

    if mode == "folder":
        res = builder.build_from_directory(
            source_dir=source,
            app_name=app_name,
            package_name=package_name,
            version_name=version,
            is_tv_compatible=is_tv,
            target_device=target_device,
            is_fullscreen=is_fullscreen,
            screen_orientation=orientation,
            icon_path=icon_path,
            theme_color=theme_color,
            extra_permissions=permissions
        )
    elif mode == "url":
        res = builder.build_from_url(
            url=source,
            app_name=app_name,
            package_name=package_name,
            version_name=version,
            is_tv_compatible=is_tv,
            target_device=target_device,
            is_fullscreen=is_fullscreen,
            screen_orientation=orientation,
            icon_path=icon_path,
            theme_color=theme_color,
            extra_permissions=permissions
        )
    elif mode == "zip":
        import tempfile, zipfile, shutil
        temp_dir = Path(tempfile.mkdtemp(prefix="wizard_zip_"))
        with zipfile.ZipFile(source, 'r') as z:
            z.extractall(temp_dir)
        htmls = list(temp_dir.glob("**/*.html"))
        target = htmls[0].parent if htmls else temp_dir
        res = builder.build_from_directory(
            source_dir=str(target),
            app_name=app_name,
            package_name=package_name,
            version_name=version,
            is_tv_compatible=is_tv,
            target_device=target_device,
            is_fullscreen=is_fullscreen,
            screen_orientation=orientation,
            icon_path=icon_path,
            theme_color=theme_color,
            extra_permissions=permissions
        )
        shutil.rmtree(temp_dir, ignore_errors=True)

    if res.get("success"):
        display_success_and_serve(res, default_port=8990, wait_for_user=True)

def check_sdk():
    print_banner()
    console.print("\n[bold cyan]🔍 Checking SDK & Toolchain Status...[/bold cyan]\n")
    status = SDKManager.check_status()

    table = Table(title="Web2APK Environment Health", border_style="cyan")
    table.add_column("Component", style="bold white")
    table.add_column("Status", style="bold")
    table.add_column("Path / Details", style="dim")

    table.add_row(
        "Java JDK 17+",
        "[green]Installed[/green]" if status["java_installed"] else "[yellow]User-Space Ready[/yellow]",
        str(status["java_home"] or "Auto-managed")
    )
    table.add_row(
        "Android Toolchain",
        "[green]Ready[/green]",
        "AAPT2 / Pure Standalone APK Engine"
    )
    table.add_row(
        "Dropzone Directory",
        "[green]Active[/green]",
        str(DROPZONE_DIR)
    )
    table.add_row(
        "Output Directory",
        "[green]Active[/green]",
        str(OUTPUT_DIR)
    )

    console.print(table)

def main():
    parser = argparse.ArgumentParser(description="Web2APK AI Agent: Universal Web to Android APK Converter, Self-Healer & Auto-Resume")
    parser.add_argument("--gui", "--studio", action="store_true", help="Launch Web2APK Studio Web Dashboard")
    parser.add_argument("--mobile", "-m", action="store_true", help="Display Project Chhaya mobile access QR code and connection links")
    parser.add_argument("--port", type=int, default=8990, help="Web Studio port (default: 8990)")
    parser.add_argument("--wizard", action="store_true", help="Run interactive terminal wizard")
    parser.add_argument("--watch", "--daemon", action="store_true", help="Start background dropzone watcher")
    parser.add_argument("--check-sdk", action="store_true", help="Check SDK & environment status")
    parser.add_argument("--growth", "--memory", action="store_true", help="Inspect agent evolution & growth memory")
    parser.add_argument("--self-heal", type=str, help="Diagnose and auto-repair a web project directory")
    parser.add_argument("--resume", action="store_true", help="Scan and auto-resume any interrupted build sessions")
    parser.add_argument("--list-models", action="store_true", help="List all dynamically discovered Gemini models")
    parser.add_argument("--set-model", type=str, help="Set Gemini model policy (e.g. 'auto' or 'gemini-3.8-flash')")
    parser.add_argument("--audit", type=str, help="Run SAST Cyber Defense security audit on a directory")
    parser.add_argument("--deploy-cloud", "--cloud", action="store_true", help="Run 24/7 Cloud Deployment Wizard")
    parser.add_argument("--surprise", type=str, help="Invent visionary surprise innovations for an app directory or name")
    parser.add_argument("--innovations", action="store_true", help="View history of all invented neural innovations")
    parser.add_argument("--inspect", type=str, help="Deep inspect a URL, folder, or ZIP and print auto-detected blueprint")
    
    # Direct build flags
    parser.add_argument("--dir", type=str, help="Source directory containing web project")
    parser.add_argument("--url", type=str, help="Live website URL to package")
    parser.add_argument("--name", type=str, default=None, help="Application display name (auto-detected if omitted)")
    parser.add_argument("--package", type=str, default=None, help="Application package ID (auto-detected if omitted)")
    parser.add_argument("--version", type=str, default="1.0.0", help="Application version")
    parser.add_argument("--theme-color", type=str, default=None, help="Theme & Status Bar color (e.g. #0f172a)")
    parser.add_argument("--orientation", type=str, default="sensor", choices=["sensor", "portrait", "landscape"], help="Screen orientation")
    parser.add_argument("--permissions", type=str, default=None, help="Comma-separated Android permissions")
    parser.add_argument("--tv", action="store_true", default=True, help="Enable Android TV & D-Pad navigation")
    parser.add_argument("--no-tv", dest="tv", action="store_false", help="Disable Android TV support")
    parser.add_argument("--target", "--device", type=str, choices=["smartphone", "tv"], default=None, help="Target device platform: smartphone or tv (default: smartphone)")
    parser.add_argument("--fullscreen", action="store_true", default=True, help="Enable immersive fullscreen")
    parser.add_argument("--icon", type=str, default=None, help="Path to custom application icon")
    parser.add_argument("--no-serve", dest="serve", action="store_false", default=True, help="Do not start Wi-Fi sideload server after build")
    parser.add_argument("--sync-github", nargs="?", const="", metavar="COMMIT_MSG", help="Commit and push all changes to GitHub origin main")
    parser.add_argument("--watch-sync", action="store_true", help="Start background automatic GitHub sync daemon")

    args = parser.parse_args()

    if args.sync_github is not None:
        print_banner()
        console.print("\n[bold cyan]🚀 Syncing Web-to-APK Agent to GitHub...[/bold cyan]")
        sync_script = Path(__file__).resolve().parent / "sync_to_github.sh"
        msg = args.sync_github.strip()
        cmd = [str(sync_script)] + ([msg] if msg else [])
        subprocess.run(cmd)
        return

    if args.watch_sync:
        print_banner()
        console.print("\n[bold cyan]🔍 Starting Antigravity Auto-Sync Watcher Daemon...[/bold cyan]")
        watcher_script = Path(__file__).resolve().parent / "scripts" / "auto_git_sync.py"
        subprocess.run([sys.executable, str(watcher_script)])
        return

    if args.inspect:
        print_banner()
        console.print(f"\n[bold cyan]🔍 Deep Multi-Source Inspection for:[/bold cyan] {args.inspect}\n")
        blueprint = AppInspector.inspect(args.inspect)
        
        table = Table(title="✨ Auto-Detected App Blueprint", border_style="cyan")
        table.add_column("Property", style="bold white")
        table.add_column("Auto-Detected Value", style="bold cyan")
        table.add_column("Detection Source / Status", style="green")

        table.add_row("App Name", blueprint["app_name"], blueprint.get("detection_sources", {}).get("app_name", "Auto"))
        table.add_row("Package ID", blueprint["package_name"], "Generated reverse domain / slug")
        table.add_row("Theme Color", blueprint["theme_color"], blueprint.get("detection_sources", {}).get("theme_color", "Inferred"))
        table.add_row("Orientation", blueprint["orientation"], blueprint.get("detection_sources", {}).get("orientation", "Default"))
        table.add_row("Fullscreen Mode", "Enabled" if blueprint["is_fullscreen"] else "Disabled", "Immersive")
        table.add_row("Android TV & D-Pad", "Enabled" if blueprint["is_tv"] else "Disabled", "Leanback + Remote")
        table.add_row("App Icon / Logo", Path(blueprint["icon_path"]).name if blueprint.get("icon_path") else "Generated Badge", blueprint.get("detection_sources", {}).get("icon", "High-Res Logo"))
        table.add_row("Detected Permissions", ", ".join([p.replace("android.permission.", "") for p in blueprint.get("detected_permissions", [])]), "JS API Scan")
        console.print(table)
    elif args.surprise:
        from web2apk.evolution import EvolutionEngine
        print_banner()
        console.print(f"\n[bold yellow]💡 Synthesizing Autonomous Surprise Innovations for:[/bold yellow] {args.surprise}\n")
        snippet = ""
        p = Path(args.surprise)
        app_title = args.name or p.name if p.exists() else args.surprise
        if p.exists():
            for f in list(p.glob("**/*.html"))[:3]:
                snippet += f.read_text(encoding="utf-8", errors="ignore") + "\n"
        
        res = EvolutionEngine.generate_surprise_innovations(app_name=app_title, html_snippet=snippet)
        if res.get("success"):
            for idx, prop in enumerate(res.get("proposals", []), 1):
                console.print(Panel(
                    f"[bold white]{prop.get('description')}[/bold white]\n\n[dim italic]\"{prop.get('tagline')}\"[/dim italic]",
                    title=f"[bold yellow]Surprise #{idx}: {prop.get('title')}[/bold yellow] ({prop.get('category')})",
                    border_style="yellow"
                ))
    elif args.innovations:
        from web2apk.evolution import EvolutionEngine
        print_banner()
        console.print("\n[bold yellow]🧠 Neural Innovations History[/bold yellow]\n")
        innovations = EvolutionEngine.load_innovations()
        if innovations:
            for inv in innovations[:5]:
                console.print(f"[bold cyan]App:[/bold cyan] {inv.get('app_name')} | [dim]Model: {inv.get('model')}[/dim]")
                for p in inv.get("proposals", [])[:3]:
                    console.print(f"  [yellow]⚡[/yellow] [bold]{p.get('title')}[/bold]: {p.get('tagline')}")
                console.print("")
        else:
            console.print("[dim]No innovations generated yet. Run --surprise to brainstorm![/dim]")
    elif args.deploy_cloud:
        print_banner()
        subprocess.run(["/bin/bash", str(Path(__file__).parent / "deploy_cloud.sh")])
    elif args.audit:
        from web2apk.security import VulnerabilityScanner
        print_banner()
        console.print(f"\n[bold red]🛡️ Running Cyber Defense Security Audit on:[/bold red] {args.audit}\n")
        report = VulnerabilityScanner.audit_directory(Path(args.audit))
        
        grade_color = "green" if report["score"] >= 85 else "yellow" if report["score"] >= 70 else "red"
        console.print(f"  [bold]Security Score:[/bold] [{grade_color}]{report['score']}/100[/{grade_color}] | [bold]Grade:[/bold] [{grade_color}]{report['grade']}[/{grade_color}]")
        console.print(f"  [bold]Files Scanned:[/bold] {report['files_scanned']} | [bold]Issues Detected:[/bold] {report['total_issues']}\n")

        if report["findings"]:
            table = Table(title="Security Vulnerabilities & Findings", border_style="red")
            table.add_column("Severity", style="bold")
            table.add_column("Vulnerability", style="bold white")
            table.add_column("Location", style="cyan")
            table.add_column("Remediation", style="dim")

            for f in report["findings"]:
                sev_style = "bold red" if f["severity"] == "CRITICAL" else "bold yellow" if f["severity"] == "HIGH" else "cyan"
                loc = f"{f['file']}:{f['line']}" if f.get("line") else f['file']
                table.add_row(f"[{sev_style}]{f['severity']}[/{sev_style}]", f["title"], loc, f["remediation"])
            console.print(table)
        else:
            console.print("[bold green]🎉 100% Clean! No security vulnerabilities discovered.[/bold green]\n")
    elif args.list_models:
        from web2apk.ai_advisor import GeminiAdvisor
        print_banner()
        console.print("\n[bold magenta]🧠 Dynamically Discovered Gemini Models[/bold magenta]\n")
        models = GeminiAdvisor.discover_available_models(force_refresh=True)
        latest = GeminiAdvisor.get_latest_flash_model()
        pref = GeminiAdvisor.get_configured_model_preference()
        
        table = Table(title=f"Gemini API Models (Current Policy: {pref})", border_style="purple")
        table.add_column("Model Name", style="bold white")
        table.add_column("Version", style="bold cyan")
        table.add_column("Status / Role", style="green")

        for m in models[:12]:
            is_top = (m["name"] == latest)
            status = "[bold green]⚡ Active (Latest)[/bold green]" if is_top else "[dim]Available[/dim]"
            table.add_row(m["name"], f"v{m['version']}", status)
        console.print(table)
        console.print(f"\n[bold cyan]Latest Auto-Selected Flash Model:[/bold cyan] [bold green]{latest}[/bold green]\n")
    elif args.set_model:
        from web2apk.ai_advisor import GeminiAdvisor
        ok = GeminiAdvisor.set_model_preference(args.set_model)
        console.print(f"[bold green]✓ Gemini model preference set to:[/bold green] {args.set_model}")
    elif args.resume:
        run_resume()
    elif args.mobile:
        print_banner()
        from web2apk.mobile_access import MobileAccessManager
        mgr = MobileAccessManager.get_instance(port=args.port)
        mgr.print_terminal_banner()
    elif args.growth:
        show_growth_memory()
    elif args.self_heal:
        run_self_heal(args.self_heal)
    elif args.check_sdk:
        check_sdk()
    elif args.watch:
        print_banner()
        start_watcher()
    elif args.wizard:
        run_wizard()
    elif args.dir or args.url:
        print_banner()
        target_source = args.dir or args.url
        console.print(f"\n[bold cyan]🔍 Auto-Inspecting source for optimal App Blueprint:[/bold cyan] {target_source}")
        blueprint = AppInspector.inspect(target_source)
        
        final_app_name = args.name or blueprint["app_name"]
        final_package = args.package or blueprint["package_name"]
        final_theme = args.theme_color or blueprint["theme_color"]
        final_orientation = args.orientation if args.orientation != "sensor" else blueprint["orientation"]
        final_icon = args.icon or blueprint.get("icon_path")
        final_perms = [p.strip() for p in args.permissions.split(",")] if args.permissions else blueprint.get("detected_permissions", [])

        console.print(f"  • [bold white]App Name:[/bold white] [bold green]{final_app_name}[/bold green]")
        console.print(f"  • [bold white]Package ID:[/bold white] [cyan]{final_package}[/cyan]")
        console.print(f"  • [bold white]Theme Color:[/bold white] [yellow]{final_theme}[/yellow]")
        console.print(f"  • [bold white]Orientation:[/bold white] [magenta]{final_orientation}[/magenta]")
        console.print(f"  • [bold white]Icon Asset:[/bold white] {Path(final_icon).name if final_icon else 'Auto generated'}")
        chosen_target = args.target
        if not chosen_target:
            chosen_target = "tv" if (args.tv and "--tv" in sys.argv) else "smartphone"
        effective_tv = (chosen_target == "tv")

        console.print(f"  • [bold white]Target Platform:[/bold white] [bold cyan]{chosen_target.capitalize()}[/bold cyan]")
        console.print(f"  • [bold white]Permissions ({len(final_perms)}):[/bold white] [dim]{', '.join([p.replace('android.permission.', '') for p in final_perms])}[/dim]\n")

        builder = APKBuilder(log_callback=lambda msg, pct: console.print(f"[bold dim][{pct}%][/bold dim] {msg}"))

        if args.dir:
            res = builder.build_from_directory(
                source_dir=args.dir,
                app_name=final_app_name,
                package_name=final_package,
                version_name=args.version,
                is_tv_compatible=effective_tv,
                target_device=chosen_target,
                is_fullscreen=args.fullscreen,
                screen_orientation=final_orientation,
                icon_path=final_icon,
                theme_color=final_theme,
                extra_permissions=final_perms
            )
        else:
            res = builder.build_from_url(
                url=args.url,
                app_name=final_app_name,
                package_name=final_package,
                version_name=args.version,
                is_tv_compatible=effective_tv,
                target_device=chosen_target,
                is_fullscreen=args.fullscreen,
                screen_orientation=final_orientation,
                icon_path=final_icon,
                theme_color=final_theme,
                extra_permissions=final_perms
            )

        if res.get("success"):
            display_success_and_serve(res, default_port=args.port, wait_for_user=args.serve)
        else:
            console.print(f"\n[bold red]❌ Build Failed:[/bold red] {res.get('error')}")
    else:
        print_banner()
        start_server(port=args.port, auto_open=True)

if __name__ == "__main__":
    main()

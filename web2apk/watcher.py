import os
import time
import shutil
import zipfile
import subprocess
from pathlib import Path
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAS_WATCHDOG = True
except ImportError:
    Observer = None
    FileSystemEventHandler = object
    HAS_WATCHDOG = False

from .builder import APKBuilder

DROPZONE_DIR = Path.home() / "Web2APK_Dropzone"
OUTPUT_DIR = Path.home() / "Web2APK_Output"

def send_notification(title: str, message: str):
    try:
        subprocess.run(["notify-send", "-i", "applications-other", title, message], check=False)
    except Exception:
        pass

class DropzoneHandler(FileSystemEventHandler):
    """
    Auto-detects newly dropped website folders or ZIP files and converts them to APK.
    Includes auto-resume on interruption.
    """

    def __init__(self):
        self.processed = set()
        self.builder = APKBuilder(log_callback=self._log)

    def _log(self, msg: str, pct: int):
        print(f"[Dropzone {pct}%] {msg}")

    def on_created(self, event):
        path = Path(event.src_path)
        
        if path.name.startswith(".") or path.name.endswith(".tmp") or str(path) in self.processed:
            return

        time.sleep(1.5)
        if not path.exists():
            return

        if path.is_file() and path.suffix.lower() == ".zip":
            self.processed.add(str(path))
            self._process_zip(path)
        elif path.is_dir():
            self.processed.add(str(path))
            self._process_directory(path)

    def _process_zip(self, zip_path: Path):
        app_name = zip_path.stem.replace("-", " ").replace("_", " ").title()
        send_notification("Web2APK Agent", f"⚡ Processing ZIP: {app_name}...")
        
        extract_dir = DROPZONE_DIR / f"_extracted_{zip_path.stem}"
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            html_files = list(extract_dir.glob("**/*.html"))
            target_dir = html_files[0].parent if html_files else extract_dir

            res = self.builder.build_from_directory(
                source_dir=str(target_dir),
                app_name=app_name,
                package_name=f"com.web2apk.{zip_path.stem.lower()}",
                is_tv_compatible=True
            )

            if res.get("success"):
                send_notification(
                    "🎉 Web2APK Build Finished!",
                    f"Created: {res['apk_name']} ({res['apk_size_mb']} MB) in ~/Web2APK_Output"
                )
            else:
                send_notification("❌ Web2APK Build Failed", f"Failed to convert {app_name}")

        except Exception as e:
            print(f"[Dropzone] Error processing {zip_path}: {e}")
        finally:
            if extract_dir.exists():
                shutil.rmtree(extract_dir, ignore_errors=True)

    def _process_directory(self, dir_path: Path):
        if dir_path.name.startswith("_extracted_"):
            return
        
        app_name = dir_path.name.replace("-", " ").replace("_", " ").title()
        send_notification("Web2APK Agent", f"⚡ Converting Folder: {app_name} to Universal APK...")

        try:
            res = self.builder.build_from_directory(
                source_dir=str(dir_path),
                app_name=app_name,
                package_name=f"com.web2apk.{dir_path.name.lower()}",
                is_tv_compatible=True
            )

            if res.get("success"):
                send_notification(
                    "🎉 Web2APK Build Finished!",
                    f"Created: {res['apk_name']} ({res['apk_size_mb']} MB) in ~/Web2APK_Output"
                )
            else:
                send_notification("❌ Web2APK Build Failed", f"Failed to convert {app_name}")
        except Exception as e:
            print(f"[Dropzone] Error processing directory {dir_path}: {e}")

def start_watcher():
    if not HAS_WATCHDOG:
        print("[!] Python 'watchdog' package is not installed. Please install it using 'pip install watchdog' to use dropzone monitoring.")
        return
    DROPZONE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    event_handler = DropzoneHandler()
    
    # Auto-resume any interrupted jobs on watcher startup
    interrupted_res = event_handler.builder.resume_interrupted_sessions()
    if interrupted_res:
        send_notification("Web2APK Auto-Resume", f"Successfully recovered and finished {len(interrupted_res)} interrupted build(s)!")

    observer = Observer()
    observer.schedule(event_handler, str(DROPZONE_DIR), recursive=False)
    observer.start()

    print(f"[*] Web2APK Dropzone Watcher active on: {DROPZONE_DIR}")
    print(f"[*] Drop any Web Folder or .zip file to auto-generate APK in: {OUTPUT_DIR}")
    send_notification("Web2APK Watcher Started", f"Monitoring {DROPZONE_DIR} with Auto-Resume enabled")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

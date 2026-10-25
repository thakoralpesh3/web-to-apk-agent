import subprocess
import shutil
import re
from pathlib import Path
from typing import List, Dict, Any

class ADBManager:
    """
    Manages Android Debug Bridge (ADB) device detection and one-click installation
    to real Android Smartphones, Tablets, and Android TV / Fire TV devices.
    """

    @classmethod
    def get_adb_path(cls) -> str:
        system_adb = shutil.which("adb")
        if system_adb:
            return system_adb
        
        # Check standard SDK platform-tools
        user_sdk = Path.home() / "Android" / "Sdk" / "platform-tools" / "adb"
        if user_sdk.exists():
            return str(user_sdk)

        return "adb"

    @classmethod
    def get_connected_devices(cls) -> List[Dict[str, Any]]:
        """
        Returns list of connected Android devices.
        """
        adb = cls.get_adb_path()
        devices = []

        try:
            res = subprocess.run([adb, "devices", "-l"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
            lines = res.stdout.strip().split("\n")[1:] # Skip 'List of devices attached'
            
            for line in lines:
                line = line.strip()
                if not line or "offline" in line:
                    continue
                
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "device":
                    dev_id = parts[0]
                    # Parse model:xxx or product:xxx
                    model_match = re.search(r"model:(\S+)", line)
                    model = model_match.group(1).replace("_", " ") if model_match else dev_id
                    
                    is_tv = "tv" in line.lower() or "leanback" in line.lower()
                    devices.append({
                        "id": dev_id,
                        "model": model,
                        "is_tv": is_tv,
                        "raw": line
                    })
        except Exception:
            pass

        return devices

    @classmethod
    def install_apk(cls, apk_path: str, device_id: str = None) -> Dict[str, Any]:
        """
        Installs APK on the target device via ADB.
        """
        adb = cls.get_adb_path()
        cmd = [adb]
        if device_id:
            cmd.extend(["-s", device_id])
        cmd.extend(["install", "-r", str(apk_path)])

        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=60)
            output = (res.stdout + "\n" + res.stderr).strip()
            success = "Success" in output

            return {
                "success": success,
                "output": output,
                "error": None if success else output
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

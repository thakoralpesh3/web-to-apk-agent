import socket
import subprocess
import shutil
import concurrent.futures
from pathlib import Path
from typing import List, Dict, Any

from .adb_manager import ADBManager

class WirelessADB:
    """
    Scans local Wi-Fi LAN for Android TVs, Google TVs, and Fire TV sticks
    with open Wireless ADB (port 5555) and allows 1-click wireless APK sideloading.
    """

    @classmethod
    def get_local_ip(cls) -> str:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Connect to non-routable address to discover outbound LAN interface
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            s.close()
        return ip

    @classmethod
    def scan_network_for_tvs(cls, timeout: float = 0.4) -> List[Dict[str, Any]]:
        """
        Scans local /24 subnet on port 5555 to discover Wireless Android TVs.
        """
        local_ip = cls.get_local_ip()
        if local_ip.startswith("127."):
            return []

        parts = local_ip.split(".")
        subnet = f"{parts[0]}.{parts[1]}.{parts[2]}"
        discovered = []

        def check_host(host_ip: str):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                res = sock.connect_ex((host_ip, 5555))
                sock.close()
                if res == 0:
                    return host_ip
            except Exception:
                pass
            return None

        # Scan 1..254 concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(check_host, f"{subnet}.{i}") for i in range(1, 255)]
            for fut in concurrent.futures.as_completed(futures):
                ip = fut.result()
                if ip:
                    # Attempt ADB connect to get device info
                    adb = ADBManager.get_adb_path()
                    try:
                        subprocess.run([adb, "connect", f"{ip}:5555"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
                    except Exception:
                        pass
                    
                    discovered.append({
                        "ip": ip,
                        "port": 5555,
                        "device_id": f"{ip}:5555",
                        "model": f"Android TV ({ip})",
                        "type": "Wireless Android TV / Google TV"
                    })

        return discovered

    @classmethod
    def install_to_wireless_tv(cls, apk_path: str, ip: str, port: int = 5555) -> Dict[str, Any]:
        """
        Connects and installs APK to target wireless Android TV.
        """
        adb = ADBManager.get_adb_path()
        target = f"{ip}:{port}"

        try:
            # 1. Connect
            subprocess.run([adb, "connect", target], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            # 2. Install
            res = ADBManager.install_apk(apk_path, device_id=target)
            return res
        except Exception as e:
            return {"success": False, "error": str(e)}

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chamunda Automobile Enterprise • Web2APK Agent
GOOGLE ARTEMIS APK AUTOMATION & DEVICE BRIDGE
Author: Aradhya (CEO), reporting to Alpesh Sir (Founder & Master Tech)
Framework: Google ARTEMIS (Pixel-Test-Engineering / PTE Fusion)
"""

from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, "/home/alpesh/chamunda_re_enterprise")
from artemis_apk_bridge import ArtemisAPKBridge, get_artemis_bridge

if __name__ == "__main__":
    bridge = get_artemis_bridge()
    devs = bridge.get_connected_devices()
    print(f"📱 Connected Devices: {len(devs)}")
    for d in devs:
        print(f"  - {d['model']} ({d['id']})")

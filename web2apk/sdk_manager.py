import os
import sys
import shutil
import tarfile
import zipfile
import subprocess
import urllib.request
from pathlib import Path
from typing import Dict, Any, Optional

SDK_DIR = Path.home() / ".web2apk"
TOOLS_DIR = SDK_DIR / "tools"
JDK_DIR = SDK_DIR / "jdk"
CACHE_DIR = SDK_DIR / "cache"

TEMURIN_JDK17_URL = "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.10%2B7/OpenJDK17U-jdk_x64_linux_hotspot_17.0.10_7.tar.gz"
ANDROID_CMDLINE_TOOLS_URL = "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip"

class SDKManager:
    """
    Autonomous toolchain manager for Web2APK.
    Provisions Java JDK 17, Android SDK tools, and Gradle in user-space.
    """

    @classmethod
    def get_java_home(cls) -> Optional[str]:
        """
        Finds existing Java 17+ or user-space JDK.
        """
        # Check user-space provisioned JDK first
        if JDK_DIR.exists():
            for sub in JDK_DIR.iterdir():
                if sub.is_dir() and (sub / "bin" / "javac").exists():
                    return str(sub)

        # Check JAVA_HOME environment variable
        env_java = os.environ.get("JAVA_HOME")
        if env_java and os.path.exists(os.path.join(env_java, "bin", "javac")):
            return env_java

        # Check system java
        system_javac = shutil.which("javac")
        if system_javac:
            real_path = os.path.realpath(system_javac)
            # /usr/lib/jvm/java-17-openjdk-amd64/bin/javac -> /usr/lib/jvm/java-17-openjdk-amd64
            java_home = str(Path(real_path).parent.parent)
            return java_home

        return None

    @classmethod
    def get_android_home(cls) -> Optional[str]:
        """
        Finds Android SDK directory.
        """
        env_android = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
        if env_android and os.path.exists(env_android):
            return env_android

        default_sdk = Path.home() / "Android" / "Sdk"
        if default_sdk.exists():
            return str(default_sdk)

        user_sdk = SDK_DIR / "android_sdk"
        if user_sdk.exists():
            return str(user_sdk)

        return None

    @classmethod
    def check_status(cls) -> Dict[str, Any]:
        """
        Checks current status of all build dependencies.
        """
        java_home = cls.get_java_home()
        android_home = cls.get_android_home()

        has_java = java_home is not None
        has_android = android_home is not None

        return {
            "java_installed": has_java,
            "java_home": java_home,
            "android_sdk_installed": has_android,
            "android_home": android_home,
            "ready_for_full_gradle": has_java and has_android,
            "ready_for_fast_build": True # Built-in AAPT2 / APK bundler mode
        }

    @classmethod
    def setup_jdk(cls, progress_callback=None) -> bool:
        """
        Downloads and provisions portable OpenJDK 17 in ~/.web2apk/jdk
        """
        if cls.get_java_home():
            if progress_callback:
                progress_callback("Java JDK already present.", 100)
            return True

        JDK_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tar_path = CACHE_DIR / "jdk17.tar.gz"

        if progress_callback:
            progress_callback("Downloading portable OpenJDK 17...", 20)

        try:
            def report_hook(block_num, block_size, total_size):
                if progress_callback and total_size > 0:
                    percent = int(20 + (block_num * block_size / total_size) * 50)
                    progress_callback(f"Downloading JDK: {percent}%", min(percent, 70))

            urllib.request.urlretrieve(TEMURIN_JDK17_URL, tar_path, reporthook=report_hook)

            if progress_callback:
                progress_callback("Extracting OpenJDK 17...", 75)

            with tarfile.open(tar_path, "r:gz") as tar:
                tar.extractall(path=JDK_DIR)

            if tar_path.exists():
                tar_path.unlink()

            if progress_callback:
                progress_callback("OpenJDK 17 setup complete!", 100)
            return True
        except Exception as e:
            print(f"[SDKManager] Failed to setup JDK: {e}")
            return False

    @classmethod
    def get_env_vars(cls) -> Dict[str, str]:
        """
        Returns environment dictionary with JAVA_HOME and PATH configured.
        """
        env = os.environ.copy()
        java_home = cls.get_java_home()
        if java_home:
            env["JAVA_HOME"] = java_home
            env["PATH"] = f"{java_home}/bin:" + env.get("PATH", "")

        android_home = cls.get_android_home()
        if android_home:
            env["ANDROID_HOME"] = android_home
            env["ANDROID_SDK_ROOT"] = android_home
            env["PATH"] = f"{android_home}/platform-tools:{android_home}/cmdline-tools/latest/bin:" + env.get("PATH", "")

        return env

import os
import re
import socket
import ipaddress
import zipfile
from urllib.parse import urlparse
from pathlib import Path
from typing import Tuple, List, Optional

class SecurityError(Exception):
    """Raised when a security policy violation is detected."""
    pass

class SSRFProtector:
    """
    Blocks Server-Side Request Forgery (SSRF) attacks by inspecting target URLs,
    resolving DNS hostnames, and rejecting private/internal networks and cloud metadata services.
    """

    BLOCKED_HOSTNAMES = {
        "localhost",
        "metadata.google.internal",
        "169.254.169.254", # AWS / GCP / Azure metadata service
        "instance-data",
        "kubernetes.default",
    }

    @classmethod
    def is_url_safe(cls, url: str) -> Tuple[bool, str]:
        if not url:
            return False, "Empty URL provided"

        try:
            parsed = urlparse(url)
            scheme = (parsed.scheme or "").lower()
            if scheme not in ("http", "https"):
                return False, f"Prohibited URL scheme '{scheme}'. Only HTTP and HTTPS are permitted."

            hostname = parsed.hostname
            if not hostname:
                return False, "Invalid URL: Missing hostname"

            hostname_lower = hostname.lower()
            if hostname_lower in cls.BLOCKED_HOSTNAMES or hostname_lower.endswith(".local") or hostname_lower.endswith(".internal"):
                return False, f"Access to internal hostname '{hostname}' is blocked by Cyber Shield."

            # Resolve DNS to check IP addresses
            try:
                addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            except socket.gaierror:
                # If DNS resolution fails, allow requests to proceed to normal fetch error handler
                return True, "Hostname unresolved"

            for family, _, _, _, sockaddr in addr_info:
                ip_str = sockaddr[0]
                ip_obj = ipaddress.ip_address(ip_str)

                # Block private, loopback, link-local, multicast, and reserved addresses
                if (
                    ip_obj.is_private
                    or ip_obj.is_loopback
                    or ip_obj.is_link_local
                    or ip_obj.is_multicast
                    or ip_obj.is_reserved
                    or ip_str.startswith("169.254.") # Cloud metadata
                ):
                    return False, f"SSRF Attack Blocked: Target '{hostname}' resolves to restricted internal IP {ip_str}."

            return True, "URL is safe"

        except Exception as e:
            return False, f"Security inspection error: {e}"

class ZipSlipProtector:
    """
    Prevents ZipSlip / Directory Traversal attacks during archive extraction.
    Ensures extracted files cannot write outside the target directory.
    """

    @classmethod
    def safe_extract_zip(cls, zip_path: Path, dest_dir: Path) -> List[Path]:
        dest_dir = dest_dir.resolve()
        dest_dir.mkdir(parents=True, exist_ok=True)
        extracted_files = []

        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.infolist():
                # Clean member path
                member_path = Path(member.filename)
                
                # Check for absolute paths or path traversal
                if member.filename.startswith("/") or member.filename.startswith("\\") or ".." in member_path.parts:
                    raise SecurityError(f"ZipSlip attack detected! Malicious entry: '{member.filename}'")

                target_path = (dest_dir / member_path).resolve()

                # Verify target path is strictly within destination directory
                try:
                    target_path.relative_to(dest_dir)
                except ValueError:
                    raise SecurityError(f"ZipSlip traversal blocked: '{member.filename}' attempts to escape target directory.")

                if member.is_dir():
                    target_path.mkdir(parents=True, exist_ok=True)
                else:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as source, open(target_path, "wb") as target:
                        target.write(source.read())
                    extracted_files.append(target_path)

        return extracted_files

class InputSanitizer:
    """
    Sanitizes user input to prevent Command Injection, Manifest Smuggling, and XSS.
    """

    @classmethod
    def sanitize_package_name(cls, package_name: str) -> str:
        # Must be valid Java package: com.example.app (only alphanumeric and dots)
        cleaned = re.sub(r"[^a-zA-Z0-9_.]", "", package_name)
        parts = [p for p in cleaned.split(".") if p]
        if len(parts) < 2:
            return "com.web2apk.app"
        return ".".join(parts)

    @classmethod
    def sanitize_app_name(cls, app_name: str) -> str:
        # Remove control characters, quotes, and dangerous symbols
        cleaned = re.sub(r'[\r\n\t"\'<>&;\\]', "", app_name).strip()
        return cleaned[:50] if cleaned else "Web App"

#!/usr/bin/env python3
"""
Automated Cyber Defense & Anti-Hacker Security Test Suite
Validates SSRF Protection, ZipSlip Defense, SAST Vulnerability Scanner,
Content-Security-Policy (CSP) injection, and Android Security Hardening.
"""

import io
import os
import sys
import zipfile
import unittest
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web2apk.security import SSRFProtector, ZipSlipProtector, InputSanitizer, SecurityError, VulnerabilityScanner, SecurityHardener
from web2apk.builder import APKBuilder

class TestCyberDefenseSuite(unittest.TestCase):

    def test_ssrf_protector_blocks_malicious_targets(self):
        """Verify SSRF Shield blocks local, private, and cloud metadata IPs."""
        # Loopback
        safe, _ = SSRFProtector.is_url_safe("http://127.0.0.1:8080/admin")
        self.assertFalse(safe)
        
        safe, _ = SSRFProtector.is_url_safe("http://localhost:3000")
        self.assertFalse(safe)

        # Cloud Metadata
        safe, _ = SSRFProtector.is_url_safe("http://169.254.169.254/latest/meta-data")
        self.assertFalse(safe)

        # Private RFC1918 IPs
        safe, _ = SSRFProtector.is_url_safe("http://192.168.1.1/router")
        self.assertFalse(safe)

        safe, _ = SSRFProtector.is_url_safe("http://10.0.0.5/internal")
        self.assertFalse(safe)

        # Invalid schemes
        safe, _ = SSRFProtector.is_url_safe("file:///etc/passwd")
        self.assertFalse(safe)

        safe, _ = SSRFProtector.is_url_safe("gopher://127.0.0.1:6379")
        self.assertFalse(safe)

        # Valid Public HTTPS URL
        safe, _ = SSRFProtector.is_url_safe("https://wikipedia.org")
        self.assertTrue(safe)

    def test_zipslip_protector_blocks_path_traversal(self):
        """Verify ZipSlip Shield detects and rejects path traversal zip entries."""
        temp_dir = Path(tempfile.mkdtemp(prefix="web2apk_sec_test_"))
        try:
            # Create a malicious zip with ../../etc/passwd entry
            malicious_zip = temp_dir / "evil.zip"
            with zipfile.ZipFile(malicious_zip, "w") as zf:
                zf.writestr("../../evil_file.txt", "MALICIOUS PAYLOAD")

            dest_dir = temp_dir / "extracted"
            with self.assertRaises(SecurityError):
                ZipSlipProtector.safe_extract_zip(malicious_zip, dest_dir)
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_vulnerability_scanner_detects_secrets_and_xss(self):
        """Verify SAST scanner flags hardcoded credentials and dangerous sinks."""
        vulnerable_code = """
        <html>
            <head><title>Vulnerable App</title></head>
            <body>
                <script>
                    const aws_key = "AKIA1234567890EXAMPLE";
                    const stripe = "sk_dummy_123456789012345678901234";
                    eval("console.log('dangerous eval')");
                    document.write("<h1>Insecure write</h1>");
                </script>
            </body>
        </html>
        """
        findings = VulnerabilityScanner.audit_code_snippet(vulnerable_code)
        self.assertGreaterEqual(len(findings), 4)

        titles = [f["title"] for f in findings]
        self.assertIn("AWS Access Key ID Leaked", titles)
        self.assertIn("Stripe Secret Key Leaked", titles)
        self.assertIn("Dangerous Code Execution (eval)", titles)
        self.assertIn("Insecure DOM Injection (document.write)", titles)

    def test_security_hardener_injects_csp_and_runtime_shield(self):
        """Verify SecurityHardener injects CSP, anti-clickjacking, and runtime isolation."""
        raw_html = "<html><head><title>Test</title></head><body><h1>Hello</h1></body></html>"
        hardened = SecurityHardener.harden_html(raw_html)

        self.assertIn("Content-Security-Policy", hardened)
        self.assertIn("X-Frame-Options", hardened)
        self.assertIn("Web2APK Cyber Defense Runtime Shield", hardened)
        self.assertIn("Object.freeze(Object.prototype.__proto__)", hardened)

    def test_full_apk_build_with_security_shield(self):
        """Verify complete APK build applies security hardening and produces security audit."""
        builder = APKBuilder()
        res = builder.build_from_directory(
            source_dir="/home/alpesh/web-to-apk-agent/samples/cyber_arcade",
            app_name="Cyber Arcade Hardened",
            package_name="com.cyber.arcade.hardened",
            is_tv_compatible=True
        )
        self.assertTrue(res["success"])
        self.assertIn("security_audit", res)
        self.assertGreaterEqual(res["security_audit"]["score"], 80)
        print(f"\n✓ Hardened APK Built: {res['apk_name']}")
        print(f"✓ Security Audit Score: {res['security_audit']['score']}/100 (Grade: {res['security_audit']['grade']})")

if __name__ == "__main__":
    unittest.main()

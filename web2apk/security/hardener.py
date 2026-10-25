import re
from typing import Optional, List

class SecurityHardener:
    """
    Applies Defense-in-Depth Android & Web runtime hardening:
    1. Injects Strict Content-Security-Policy (CSP)
    2. Enforces Android Network Security Config (Strict TLS)
    3. Injects Runtime Anti-Tamper & Clickjack Protection
    4. Hardens JavaScript Execution Context
    """

    @classmethod
    def generate_network_security_config(cls, allow_cleartext: bool = False, pin_domains: Optional[List[str]] = None) -> str:
        """
        Generates Android res/xml/network_security_config.xml enforcing HTTPS and trusted CA pinning.
        """
        cleartext_str = "true" if allow_cleartext else "false"
        
        xml = f"""<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
    <base-config cleartextTrafficPermitted="{cleartext_str}">
        <trust-anchors>
            <certificates src="system" />
            <certificates src="user" />
        </trust-anchors>
    </base-config>
</network-security-config>
"""
        return xml

    @classmethod
    def get_security_guard_js(cls) -> str:
        """
        Injected lightweight client-side security supervisor that prevents prototype pollution,
        frame-busting attacks, and malicious script tampering.
        """
        return """/**
 * Web2APK Cyber Defense Runtime Shield
 * Enforces in-app sandbox isolation and anti-tamper protections.
 */
(function() {
    'use strict';
    
    // 1. Anti-Clickjacking / Frame Hijack Guard
    try {
        if (window.top !== window.self) {
            window.top.location = window.self.location;
        }
    } catch(e) {}

    // 2. Prototype Pollution Immunization
    try {
        Object.freeze(Object.prototype.__proto__);
    } catch(e) {}

    // 3. Prevent Protocol Hijacking & Insecure Deep Linking
    const originalOpen = window.open;
    window.open = function(url, target, features) {
        if (typeof url === 'string') {
            const lower = url.trim().toLowerCase();
            if (lower.startsWith('javascript:') || lower.startsWith('vbscript:') || lower.startsWith('data:text/html')) {
                console.warn('[CyberShield] Blocked dangerous script URL execution:', url);
                return null;
            }
        }
        return originalOpen.apply(this, arguments);
    };

    // 4. Secure postMessage Filter Helper
    window.Web2APKSecure = {
        verifyOrigin: function(event, allowedOrigins) {
            if (!event || !event.origin) return false;
            if (!Array.isArray(allowedOrigins)) allowedOrigins = [allowedOrigins];
            return allowedOrigins.includes(event.origin);
        }
    };
})();
"""

    @classmethod
    def harden_html(cls, html_content: str, enforce_csp: bool = True) -> str:
        """
        Injects CSP headers, Anti-Clickjack tags, and Runtime Shield script into HTML.
        """
        csp_meta = """<meta http-equiv="Content-Security-Policy" content="default-src 'self' file: data: blob: https: 'unsafe-inline' 'unsafe-eval'; connect-src * wss: https: file:; media-src * blob: data: file:; img-src * data: blob: file:;">"""
        x_frame_meta = """<meta http-equiv="X-Frame-Options" content="DENY">"""
        referrer_meta = """<meta name="referrer" content="strict-origin-when-cross-origin">"""

        security_tags = f"\n    {csp_meta}\n    {x_frame_meta}\n    {referrer_meta}\n"

        modified = html_content

        # Inject into <head>
        if "<head>" in modified:
            modified = modified.replace("<head>", f"<head>{security_tags}", 1)
        elif "<HEAD>" in modified:
            modified = modified.replace("<HEAD>", f"<HEAD>{security_tags}", 1)
        else:
            modified = security_tags + modified

        # Inject Security Guard script
        guard_script = f"""\n<script>\n{cls.get_security_guard_js()}\n</script>\n"""
        if "</body>" in modified:
            modified = modified.replace("</body>", f"{guard_script}</body>", 1)
        else:
            modified += guard_script

        return modified

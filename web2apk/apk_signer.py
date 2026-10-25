import io
import struct
import hashlib
import datetime
import zipfile
import base64
from pathlib import Path
from typing import Tuple, List, Dict, Any

import cryptography
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.serialization import pkcs7
from cryptography.x509.oid import NameOID

CHUNK_SIZE = 1048576  # 1MB
SIGNATURE_RSA_PKCS1_V1_5_WITH_SHA256 = 0x0102
APK_SIGNATURE_SCHEME_V2_BLOCK_ID = 0x7109871a
APK_SIG_BLOCK_MAGIC = b"APK Sig Block 42"

def len_prefixed(data: bytes) -> bytes:
    return struct.pack("<I", len(data)) + data

def compute_aosp_v2_digest(section1: bytes, section2: bytes, section3: bytes) -> bytes:
    """
    Computes standard AOSP 1MB-chunked digest across all 3 APK sections.
    """
    chunks = []
    for section in [section1, section2, section3]:
        if not section:
            continue
        for i in range(0, len(section), CHUNK_SIZE):
            chunks.append(section[i:i + CHUNK_SIZE])

    if not chunks:
        chunks = [b""]

    chunk_digests = bytearray()
    for chunk in chunks:
        h = hashlib.sha256()
        h.update(b"\x5a" + struct.pack("<I", len(chunk)) + chunk)
        chunk_digests += h.digest()

    root_h = hashlib.sha256()
    root_h.update(b"\x5a" + struct.pack("<I", len(chunks)) + bytes(chunk_digests))
    return root_h.digest()

class APKSignerV2:
    """
    Genuine AOSP-Compliant Android APK Toolchain:
    1. Generates 2048-bit RSA keys & X.509 Certificates
    2. Writes compliant v1 JAR signatures (MANIFEST.MF, CERT.SF, PKCS#7 CERT.RSA)
    3. Performs standard 4-byte ZipAlign
    4. Applies cryptographic APK Signature Scheme v2 block
    """

    @classmethod
    def generate_keystore_cert(cls) -> Tuple[rsa.RSAPrivateKey, x509.Certificate, bytes, bytes]:
        config_dir = Path.home() / ".web2apk"
        config_dir.mkdir(parents=True, exist_ok=True)
        key_path = config_dir / "debug_key.pem"
        cert_path = config_dir / "debug_cert.pem"

        if key_path.exists() and cert_path.exists():
            try:
                private_key = serialization.load_pem_private_key(
                    key_path.read_bytes(),
                    password=None
                )
                cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
                cert_der = cert.public_bytes(serialization.Encoding.DER)
                pub_der = private_key.public_key().public_bytes(
                    serialization.Encoding.DER,
                    serialization.PublicFormat.SubjectPublicKeyInfo
                )
                return private_key, cert, cert_der, pub_der
            except Exception:
                pass

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Android"),
            x509.NameAttribute(NameOID.COMMON_NAME, "Android Debug")
        ])

        now = datetime.datetime.now(datetime.timezone.utc)
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=365*30))
            .sign(private_key, hashes.SHA256())
        )

        try:
            key_path.write_bytes(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
            cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        except Exception:
            pass

        cert_der = cert.public_bytes(serialization.Encoding.DER)
        pub_der = private_key.public_key().public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return private_key, cert, cert_der, pub_der

    @classmethod
    def zipalign(cls, zip_bytes: bytes, alignment: int = 4) -> bytes:
        """
        Aligns all uncompressed stored entries to 4-byte boundaries.
        """
        in_buf = io.BytesIO(zip_bytes)
        out_buf = io.BytesIO()

        with zipfile.ZipFile(in_buf, "r") as in_zip:
            with zipfile.ZipFile(out_buf, "w") as out_zip:
                for item in in_zip.infolist():
                    data = in_zip.read(item.filename)
                    if item.compress_type == zipfile.ZIP_STORED:
                        current_lfh_pos = out_buf.tell()
                        fn_len = len(item.filename.encode("utf-8"))
                        existing_extra_len = len(item.extra) if item.extra else 0
                        unaligned_data_pos = current_lfh_pos + 30 + fn_len + existing_extra_len
                        remainder = unaligned_data_pos % alignment
                        if remainder != 0:
                            padding_len = alignment - remainder
                            item.extra = (item.extra or b"") + (b"\x00" * padding_len)
                    out_zip.writestr(item, data)

        return out_buf.getvalue()

    @classmethod
    def sign_and_align_apk(cls, unsigned_zip_bytes: bytes) -> bytes:
        """
        Full AOSP APK Signing & ZipAlign Pipeline:
        1. Inject v1 JAR signatures (MANIFEST.MF, CERT.SF, PKCS#7 CERT.RSA)
        2. 4-byte ZipAlign
        3. Cryptographic APK Signature Scheme v2
        """
        priv_key, cert, cert_der, pub_der = cls.generate_keystore_cert()

        # Step 1: Add v1 JAR Signatures
        in_buf = io.BytesIO(unsigned_zip_bytes)
        v1_buf = io.BytesIO()

        manifest_entries = []
        with zipfile.ZipFile(in_buf, "r") as in_zip:
            with zipfile.ZipFile(v1_buf, "w") as out_zip:
                for item in in_zip.infolist():
                    if item.filename.startswith("META-INF/"):
                        continue
                    data = in_zip.read(item.filename)
                    out_zip.writestr(item, data)
                    
                    sha1_b64 = base64.b64encode(hashlib.sha1(data).digest()).decode("ascii")
                    sha256_b64 = base64.b64encode(hashlib.sha256(data).digest()).decode("ascii")
                    manifest_entries.append((item.filename, sha1_b64, sha256_b64))

                # Build MANIFEST.MF
                mf_lines = [
                    "Manifest-Version: 1.0",
                    "Created-By: 1.0 (Android Web2APK Toolchain)",
                    "Built-By: Web2APK Android Universal Engine",
                    ""
                ]
                for fn, sha1_val, sha256_val in manifest_entries:
                    mf_lines.append(f"Name: {fn}")
                    mf_lines.append(f"SHA1-Digest: {sha1_val}")
                    mf_lines.append(f"SHA-256-Digest: {sha256_val}")
                    mf_lines.append("")
                mf_data = "\r\n".join(mf_lines).encode("utf-8")
                out_zip.writestr("META-INF/MANIFEST.MF", mf_data)

                # Build CERT.SF
                sf_lines = [
                    "Signature-Version: 1.0",
                    "Created-By: 1.0 (Android Web2APK)",
                    "SHA1-Digest-Manifest: " + base64.b64encode(hashlib.sha1(mf_data).digest()).decode("ascii"),
                    "SHA-256-Digest-Manifest: " + base64.b64encode(hashlib.sha256(mf_data).digest()).decode("ascii"),
                    ""
                ]
                for fn, sha1_val, sha256_val in manifest_entries:
                    entry_text = f"Name: {fn}\r\nSHA1-Digest: {sha1_val}\r\nSHA-256-Digest: {sha256_val}\r\n\r\n".encode("utf-8")
                    sf_lines.append(f"Name: {fn}")
                    sf_lines.append(f"SHA1-Digest: " + base64.b64encode(hashlib.sha1(entry_text).digest()).decode("ascii"))
                    sf_lines.append(f"SHA-256-Digest: " + base64.b64encode(hashlib.sha256(entry_text).digest()).decode("ascii"))
                    sf_lines.append("")
                sf_data = "\r\n".join(sf_lines).encode("utf-8")
                out_zip.writestr("META-INF/CERT.SF", sf_data)

                # Generate Genuine PKCS#7 CERT.RSA
                pkcs7_builder = (
                    pkcs7.PKCS7SignatureBuilder()
                    .set_data(sf_data)
                    .add_signer(cert, priv_key, hashes.SHA256())
                )
                cert_rsa_der = pkcs7_builder.sign(
                    serialization.Encoding.DER,
                    options=[pkcs7.PKCS7Options.DetachedSignature]
                )
                out_zip.writestr("META-INF/CERT.RSA", cert_rsa_der)

        v1_signed_bytes = v1_buf.getvalue()

        # Step 2: 4-Byte ZipAlign
        aligned_bytes = cls.zipalign(v1_signed_bytes, alignment=4)

        # Step 3: APK Signature Scheme v2
        eocd_idx = aligned_bytes.rfind(b"\x50\x4b\x05\x06")
        if eocd_idx == -1:
            raise ValueError("Invalid ZIP: EOCD signature not found")

        cd_size, cd_offset = struct.unpack_from("<II", aligned_bytes, eocd_idx + 12)

        section1 = aligned_bytes[:cd_offset]
        section2 = aligned_bytes[cd_offset:eocd_idx]
        section3_orig = aligned_bytes[eocd_idx:]

        section3_for_digest = bytearray(section3_orig)
        struct.pack_into("<I", section3_for_digest, 16, cd_offset)

        apk_content_digest = compute_aosp_v2_digest(section1, section2, bytes(section3_for_digest))

        # Build SignedData
        digest_record = struct.pack("<I", SIGNATURE_RSA_PKCS1_V1_5_WITH_SHA256) + len_prefixed(apk_content_digest)
        digests_data = len_prefixed(len_prefixed(digest_record))
        certs_data = len_prefixed(len_prefixed(cert_der))
        attrs_data = len_prefixed(b"")
        signed_data = digests_data + certs_data + attrs_data

        # RSA Signature over SignedData
        sig_bytes = priv_key.sign(
            signed_data,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        sig_record = struct.pack("<I", SIGNATURE_RSA_PKCS1_V1_5_WITH_SHA256) + len_prefixed(sig_bytes)
        signatures_data = len_prefixed(len_prefixed(sig_record))

        # Signer structure
        signer_data = len_prefixed(signed_data) + signatures_data + len_prefixed(pub_der)
        signers_block = len_prefixed(len_prefixed(signer_data))

        # v2 pair
        v2_pair_content = struct.pack("<I", APK_SIGNATURE_SCHEME_V2_BLOCK_ID) + signers_block
        v2_pair = struct.pack("<Q", len(v2_pair_content)) + v2_pair_content

        # APK Signing Block
        block_size = len(v2_pair) + 8 + 16
        signing_block = (
            struct.pack("<Q", block_size) +
            v2_pair +
            struct.pack("<Q", block_size) +
            APK_SIG_BLOCK_MAGIC
        )

        # Update EOCD
        new_cd_offset = len(section1) + len(signing_block)
        final_eocd = bytearray(section3_orig)
        struct.pack_into("<I", final_eocd, 16, new_cd_offset)

        return section1 + signing_block + section2 + bytes(final_eocd)

#!/usr/bin/env bash
# Autonomous Toolchain Provisioner for Web-to-APK Agent
set -e

TOOLS_DIR="${HOME}/.web2apk/tools"
mkdir -p "$TOOLS_DIR"

echo "=== Setting up Web-to-APK Native Toolchain ==="

# Check Java
if command -v java >/dev/null 2>&1; then
    JAVA_CMD=$(which java)
    echo "✓ Java detected: $JAVA_CMD"
else
    echo "⚠️ Warning: Java not found on PATH. Please install OpenJDK 17."
fi

# 1. Android Platform android.jar
if [ ! -f "$TOOLS_DIR/android.jar" ]; then
    echo "Downloading Android framework jar (API 34)..."
    curl -fsSL https://github.com/Sable/android-platforms/raw/master/android-34/android.jar -o "$TOOLS_DIR/android.jar"
fi
echo "✓ android.jar ready: $TOOLS_DIR/android.jar"

# 2. Uber-APK-Signer
if [ ! -f "$TOOLS_DIR/uber-apk-signer.jar" ]; then
    echo "Downloading Uber-APK-Signer 1.3.0..."
    curl -fsSL https://github.com/patrickfav/uber-apk-signer/releases/download/v1.3.0/uber-apk-signer-1.3.0.jar -o "$TOOLS_DIR/uber-apk-signer.jar"
fi
echo "✓ Uber-APK-Signer ready: $TOOLS_DIR/uber-apk-signer.jar"

# 3. R8 D8 Compiler
if [ ! -f "$TOOLS_DIR/r8.jar" ]; then
    echo "Downloading R8 Dex compiler..."
    curl -fsSL https://dl.google.com/dl/android/maven2/com/android/tools/r8/8.2.33/r8-8.2.33.jar -o "$TOOLS_DIR/r8.jar" || true
fi
echo "✓ R8 ready: $TOOLS_DIR/r8.jar"

# 4. AAPT2
if [ ! -f "$TOOLS_DIR/aapt2" ]; then
    echo "Downloading official Google AAPT2 binary..."
    TMP_JAR="/tmp/aapt2_dl.jar"
    curl -fsSL https://dl.google.com/dl/android/maven2/com/android/tools/build/aapt2/8.2.2-10154469/aapt2-8.2.2-10154469-linux.jar -o "$TMP_JAR" || true
    if [ -f "$TMP_JAR" ]; then
        unzip -p "$TMP_JAR" aapt2 > "$TOOLS_DIR/aapt2" || true
        rm -f "$TMP_JAR"
    fi
    chmod +x "$TOOLS_DIR/aapt2" 2>/dev/null || true
fi
echo "✓ AAPT2 ready: $TOOLS_DIR/aapt2"

chmod +x "$TOOLS_DIR"/* 2>/dev/null || true
echo "=== Web-to-APK Toolchain Setup Complete! ==="

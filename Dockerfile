FROM python:3.12-slim

# Install system utilities and runtime libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    lib32z1 \
    libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . /app

# Setup Web2APK system directories and tools
RUN mkdir -p /root/.web2apk/tools /root/.web2apk/workspaces /root/.web2apk/url_cache /root/Web2APK_Output && \
    if [ -f /root/.web2apk/tools/aapt2 ]; then chmod +x /root/.web2apk/tools/aapt2; fi

# Copy tools from host setup if available
COPY --from=0 /root/.web2apk/tools/aapt2 /root/.web2apk/tools/aapt2 2>/dev/null || true
COPY --from=0 /root/.web2apk/tools/android.jar /root/.web2apk/tools/android.jar 2>/dev/null || true

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8990

# Expose Web Studio port
EXPOSE 8990

# Run Web2APK AI Studio Web Service
CMD ["python3", "agent.py", "--gui", "--port", "8990"]

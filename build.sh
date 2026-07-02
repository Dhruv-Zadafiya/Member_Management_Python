#!/usr/bin/env bash
# Render build script
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
mkdir -p static/exports
mkdir -p static/fonts

# Download Noto Sans Gujarati font for PDF export (supports Gujarati Unicode text)
if [ ! -f static/fonts/NotoSansGujarati-Regular.ttf ]; then
    echo "Downloading Noto Sans Gujarati font..."
    curl -L -o static/fonts/NotoSansGujarati-Regular.ttf \
        "https://raw.githubusercontent.com/google/fonts/main/ofl/notosansgujarati/static/NotoSansGujarati-Regular.ttf"
fi

echo "Build completed successfully!"

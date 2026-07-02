#!/usr/bin/env bash
# Render build script
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
mkdir -p static/exports
mkdir -p static/fonts

# Download fonts for PDF export
# NotoSans - for Latin text (English, numbers, dates)
if [ ! -f static/fonts/NotoSans-Regular.ttf ]; then
    echo "Downloading Noto Sans font..."
    curl -L -o static/fonts/NotoSans-Regular.ttf \
        "https://cdn.jsdelivr.net/fontsource/fonts/noto-sans@latest/latin-400-normal.ttf"
fi

# NotoSansGujarati - for Gujarati Unicode text
if [ ! -f static/fonts/NotoSansGujarati-Regular.ttf ]; then
    echo "Downloading Noto Sans Gujarati font..."
    curl -L -o static/fonts/NotoSansGujarati-Regular.ttf \
        "https://cdn.jsdelivr.net/fontsource/fonts/noto-sans-gujarati@latest/gujarati-400-normal.ttf"
fi

echo "Build completed successfully!"

## 🚀 New Features

### Jinja2 Templating System
- Full Jinja2 template support for notification customization
- **20+ template variables** available: `{{camera}}`, `{{object}}`, `{{sub_label}}`, `{{location}}`, `{{genai_description}}`, etc.
- **Object-specific templates** - Customize messages for person, car, dog, etc.
- **Severity-specific templates** - Different formats for alerts vs detections
- **Camera-specific templates** - Per-camera customization

### Image Compression
- **Prevents Android app crashes** from large images
- Configurable max dimensions (default: 640x480)
- Iterative quality reduction to meet target file size (default: 100KB)
- Maintains aspect ratio when resizing
- Converts RGBA/PNG to JPEG for better compression

## 🔧 Configuration

### New Environment Variables
```bash
# Image Compression
IMAGE_COMPRESSION_ENABLED=true
IMAGE_MAX_WIDTH=640
IMAGE_MAX_HEIGHT=480
IMAGE_QUALITY=75
IMAGE_MAX_SIZE_KB=100

# Templating
TITLE_TEMPLATE=[{{ severity|upper }}] {{ camera }}
MESSAGE_TEMPLATE={{ camera }} detected {{ object }} in {{ location }}.
```

## 📦 Docker
```bash
docker pull ghcr.io/tomatomonster69/frigate-gotify:latest
docker pull ghcr.io/tomatomonster69/frigate-gotify:v1.1.0
```

## 🐛 Bug Fixes
- SSL certificate handling for self-signed certificates
- Base64 image embedding for remote client compatibility

## 📝 Full Changelog
- Added: `src/template_engine.py` - Jinja2 template engine
- Added: `src/image_compressor.py` - Image compression utility
- Updated: `src/gotify_client.py` - Compression integration
- Updated: `src/config.py` - New configuration options
- Updated: `.env.example` - Comprehensive documentation
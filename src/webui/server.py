"""FastAPI web server for template configuration UI."""

import logging
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..config import settings
from ..template_engine import TemplateEngine

logger = logging.getLogger(__name__)

# Template variables available for selection
TEMPLATE_VARIABLES = [
    {"name": "camera", "description": "Camera ID (e.g., front_door)"},
    {"name": "camera_name", "description": "Camera name (e.g., Front Door)"},
    {"name": "object", "description": "Detected object (person, car, etc.)"},
    {"name": "object_label", "description": "Same as object"},
    {"name": "sub_label", "description": "Sub-category (license_plate, UPS)"},
    {"name": "location", "description": "Location/zone name"},
    {"name": "zone", "description": "Alias for location"},
    {"name": "zones", "description": "List of all zones"},
    {"name": "severity", "description": "Event severity (alert, detection)"},
    {"name": "genai_description", "description": "AI-generated summary"},
    {"name": "genai", "description": "Alias for genai_description"},
    {"name": "ai_summary", "description": "Alias for genai_description"},
    {"name": "audio", "description": "List of detected audio"},
    {"name": "audio_detected", "description": "Comma-separated audio"},
    {"name": "timestamp", "description": "Event timestamp"},
    {"name": "time", "description": "Alias for timestamp"},
    {"name": "score", "description": "Detection confidence (0-1)"},
    {"name": "confidence", "description": "Formatted confidence (85%)"},
    {"name": "object_display", "description": "Object with sub-label"},
]

# Sample data for preview
SAMPLE_DATA = {
    "camera": "front_door",
    "camera_name": "Front Door",
    "object": "person",
    "object_label": "person",
    "sub_label": "UPS Driver",
    "location": "Front Yard",
    "zone": "Front Yard",
    "zones": ["Front Yard", "Driveway"],
    "severity": "detection",
    "genai_description": "A delivery person in a brown uniform was detected approaching the front door with a package.",
    "genai": "A delivery person in a brown uniform was detected approaching the front door with a package.",
    "ai_summary": "A delivery person in a brown uniform was detected approaching the front door with a package.",
    "audio": ["doorbell"],
    "audio_detected": "doorbell",
    "timestamp": "2026-03-09 14:32:15",
    "time": "2026-03-09 14:32:15",
    "score": 0.92,
    "confidence": "92%",
    "object_display": "person (UPS Driver)",
}

# Preset templates
PRESET_TEMPLATES = [
    {
        "name": "Generic",
        "title": "{{camera_name}} - {{object}} detected",
        "message": "{{camera}} detected {{object}}{% if sub_label %} ({{sub_label}}){% endif %} in {{location}}.{% if genai_description %}\n\n{{genai_description}}{% endif %}",
    },
    {
        "name": "Detailed",
        "title": "[{{severity|upper}}] {{camera_name}}",
        "message": "Detected: {{object_display}}\nLocation: {{location}}\nTime: {{timestamp}}{% if genai_description %}\n\n**AI Analysis:** {{genai_description}}{% endif %}",
    },
    {
        "name": "Minimal",
        "title": "{{object|title}} at {{camera_name}}",
        "message": "{% if genai_description %}{{genai_description}}{% else %}{{object}} detected in {{location}}{% endif %}",
    },
]


class ConfigSaveRequest(BaseModel):
    """Full configuration save request."""
    # Frigate Settings
    frigate_url: str
    frigate_api_key: Optional[str] = None
    frigate_username: Optional[str] = None
    frigate_password: Optional[str] = None
    
    # Gotify Settings
    gotify_url: str
    gotify_app_token: str
    
    # SSL Settings
    verify_ssl: bool = False
    
    # Polling Settings
    poll_interval: int = 10
    
    # Notification Settings
    notification_priority: int = 5
    include_snapshot: bool = True
    snapshot_quality: int = 90
    snapshot_format: str = "jpg"
    
    # Image Compression Settings
    image_compression_enabled: bool = True
    image_max_width: int = 640
    image_max_height: int = 480
    image_quality: int = 75
    image_max_size_kb: int = 100
    
    # Filter Settings - Toggles for each severity
    filter_alerts: bool = True
    filter_detections: bool = True
    camera_filter: str = "all"
    
    # Template Settings
    title_template: Optional[str] = None
    message_template: Optional[str] = None
    
    # Debug
    debug: bool = False


class TemplatePreviewRequest(BaseModel):
    """Template preview request."""
    title_template: str
    message_template: str


class TestAlertRequest(BaseModel):
    """Test alert request (optional title/message)."""
    title: Optional[str] = None
    message: Optional[str] = None


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Frigate-Gotify Config")
    
    webui_dir = Path(__file__).parent
    static_dir = webui_dir / "static"
    static_dir.mkdir(exist_ok=True)
    
    @app.get("/", response_class=HTMLResponse)
    async def index():
        """Serve the main HTML page."""
        html_file = webui_dir / "templates" / "index.html"
        if not html_file.exists():
            return HTMLResponse(content="<h1>Template not found</h1>", status_code=404)
        return HTMLResponse(content=html_file.read_text())
    
    @app.get("/api/variables")
    async def get_variables():
        """Get available template variables."""
        return {"variables": TEMPLATE_VARIABLES}
    
    @app.get("/api/presets")
    async def get_presets():
        """Get preset templates."""
        return {"presets": PRESET_TEMPLATES}
    
    @app.post("/api/test")
    async def test_alert(request: TestAlertRequest):
        """Send a test notification to Gotify."""
        from ..gotify_client import GotifyClient
        from ..config import settings
        
        try:
            gotify = GotifyClient()
            title = request.title or "Test Notification"
            message = request.message or "This is a test notification from Frigate-Gotify!"
            
            success = await gotify.send_message(title=title, message=message)
            
            return {
                "success": success,
                "message": "Test notification sent!" if success else "Failed to send test notification",
            }
        except Exception as e:
            logger.error(f"Error sending test alert: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/config")
    async def get_config():
        """Get current configuration."""
        # Parse severity filter into toggles
        severity_filter = settings.severity_filter.lower()
        filter_alerts = "alert" in severity_filter
        filter_detections = "detection" in severity_filter
        
        return {
            # Frigate Settings
            "frigate_url": settings.frigate_url,
            "frigate_api_key": settings.frigate_api_key or "",
            "frigate_username": settings.frigate_username or "",
            "frigate_password": settings.frigate_password or "",
            
            # Gotify Settings
            "gotify_url": settings.gotify_url,
            "gotify_app_token": settings.gotify_app_token[:8] + "..." if settings.gotify_app_token else "",
            
            # SSL Settings
            "verify_ssl": settings.verify_ssl,
            
            # Polling Settings
            "poll_interval": settings.poll_interval,
            
            # Notification Settings
            "notification_priority": settings.notification_priority,
            "include_snapshot": settings.include_snapshot,
            "snapshot_quality": settings.snapshot_quality,
            "snapshot_format": settings.snapshot_format,
            
            # Image Compression Settings
            "image_compression_enabled": settings.image_compression_enabled,
            "image_max_width": settings.image_max_width,
            "image_max_height": settings.image_max_height,
            "image_quality": settings.image_quality,
            "image_max_size_kb": settings.image_max_size_kb,
            
            # Filter Settings - Toggles
            "filter_alerts": filter_alerts,
            "filter_detections": filter_detections,
            "camera_filter": settings.camera_filter,
            
            # Template Settings
            "title_template": settings.title_template or PRESET_TEMPLATES[0]["title"],
            "message_template": settings.message_template or PRESET_TEMPLATES[0]["message"],
            
            # Debug
            "debug": settings.debug,
        }
    
    @app.post("/api/preview")
    async def preview_template(request: TemplatePreviewRequest):
        """Preview a template with sample data."""
        try:
            engine = TemplateEngine(
                title_template=request.title_template,
                message_template=request.message_template,
            )
            
            title = engine.render_title(
                camera=SAMPLE_DATA["camera"],
                severity=SAMPLE_DATA["severity"],
                sub_label=SAMPLE_DATA["sub_label"],
                location=SAMPLE_DATA["location"],
            )
            
            message = engine.render_message(
                camera=SAMPLE_DATA["camera"],
                object_label=SAMPLE_DATA["object"],
                sub_label=SAMPLE_DATA["sub_label"],
                location=SAMPLE_DATA["location"],
                severity=SAMPLE_DATA["severity"],
                genai_description=SAMPLE_DATA["genai_description"],
                zones=SAMPLE_DATA["zones"],
                audio=SAMPLE_DATA["audio"],
                timestamp=SAMPLE_DATA["timestamp"],
                score=SAMPLE_DATA["score"],
            )
            
            return {
                "title": title,
                "message": message,
                "sample_data": SAMPLE_DATA,
            }
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.post("/api/save")
    async def save_config(request: ConfigSaveRequest):
        """Save full configuration to .env file."""
        try:
            config_dir = Path("/app/config")
            config_dir.mkdir(exist_ok=True)
            
            env_file = config_dir / ".env"
            
            # Build severity filter from toggles
            severity_parts = []
            if request.filter_alerts:
                severity_parts.append("alert")
            if request.filter_detections:
                severity_parts.append("detection")
            severity_filter = ",".join(severity_parts) if severity_parts else "alert,detection"
            
            def escape_env_value(value: str) -> str:
                """Escape value for .env file, quoting if it contains special chars."""
                if not value:
                    return '""'
                # Convert newlines to literal \n escape sequence for proper .env parsing
                escaped = value.replace('\\', '\\\\').replace('\n', '\\n').replace('"', '\\"')
                # Check if value needs quoting (contains special chars)
                if ' ' in value.strip() or '#' in value or '"' in value:
                    return f'"{escaped}"'
                return escaped
            
            # Build .env content
            lines = [
                "# Frigate-Gotify Configuration",
                "# Generated by Web UI",
                "",
                "# Frigate Settings",
                f"FRIGATE_URL={escape_env_value(request.frigate_url)}",
            ]
            
            if request.frigate_api_key:
                lines.append(f"FRIGATE_API_KEY={escape_env_value(request.frigate_api_key)}")
            if request.frigate_username:
                lines.append(f"FRIGATE_USERNAME={escape_env_value(request.frigate_username)}")
            if request.frigate_password:
                lines.append(f"FRIGATE_PASSWORD={escape_env_value(request.frigate_password)}")
            
            lines.extend([
                "",
                "# Gotify Settings",
                f"GOTIFY_URL={escape_env_value(request.gotify_url)}",
                f"GOTIFY_APP_TOKEN={escape_env_value(request.gotify_app_token)}",
                "",
                "# SSL Settings",
                f"VERIFY_SSL={'true' if request.verify_ssl else 'false'}",
                "",
                "# Polling Settings",
                f"POLL_INTERVAL={request.poll_interval}",
                "",
                "# Notification Settings",
                f"NOTIFICATION_PRIORITY={request.notification_priority}",
                f"INCLUDE_SNAPSHOT={'true' if request.include_snapshot else 'false'}",
                f"SNAPSHOT_QUALITY={request.snapshot_quality}",
                f"SNAPSHOT_FORMAT={escape_env_value(request.snapshot_format)}",
                "",
                "# Image Compression Settings",
                f"IMAGE_COMPRESSION_ENABLED={'true' if request.image_compression_enabled else 'false'}",
                f"IMAGE_MAX_WIDTH={request.image_max_width}",
                f"IMAGE_MAX_HEIGHT={request.image_max_height}",
                f"IMAGE_QUALITY={request.image_quality}",
                f"IMAGE_MAX_SIZE_KB={request.image_max_size_kb}",
                "",
                "# Filter Settings",
                f"SEVERITY_FILTER={escape_env_value(severity_filter)}",
                f"CAMERA_FILTER={escape_env_value(request.camera_filter)}",
                "",
                "# Template Settings",
            ])
            
            if request.title_template:
                lines.append(f"TITLE_TEMPLATE={escape_env_value(request.title_template)}")
            if request.message_template:
                lines.append(f"MESSAGE_TEMPLATE={escape_env_value(request.message_template)}")
            
            lines.extend([
                "",
                "# Debug Settings",
                f"DEBUG={'true' if request.debug else 'false'}",
            ])
            
            env_file.write_text("\n".join(lines) + "\n")
            logger.info(f"Configuration saved to {env_file}")
            
            return {
                "success": True,
                "message": "Configuration saved! Click 'Restart' to apply changes.",
                "file": str(env_file),
            }
        except PermissionError as e:
            logger.error(f"Permission denied writing config: {e}")
            raise HTTPException(
                status_code=500,
                detail="Cannot write to config directory. Check volume permissions."
            )
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/restart")
    async def restart_container():
        """Restart the container by exiting (Docker/compose will restart it)."""
        import os
        import signal
        
        logger.info("Container restart requested via Web UI")
        
        # Send SIGTERM to ourselves - Docker/compose will handle restart
        # This is safer than trying to run docker commands from inside
        try:
            # Schedule the exit for a moment later so response can be sent
            import threading
            def delayed_exit():
                import time
                time.sleep(1)  # Give time for response to be sent
                logger.info("Shutting down for restart...")
                os.kill(os.getpid(), signal.SIGTERM)
            
            thread = threading.Thread(target=delayed_exit, daemon=True)
            thread.start()
            
            return {
                "success": True,
                "message": "Container is restarting... The service will be unavailable briefly."
            }
        except Exception as e:
            logger.error(f"Error during restart: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Serve static files
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    return app

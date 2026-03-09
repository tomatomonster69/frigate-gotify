"""FastAPI web server for template configuration UI."""

import os
import logging
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..config import settings
from ..template_engine import TemplateEngine, parse_template_config

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


class TemplateSaveRequest(BaseModel):
    title_template: str
    message_template: str


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Frigate-Gotify Config")
    
    # Get the directory containing static files
    webui_dir = Path(__file__).parent
    
    # Mount static files
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
    
    @app.get("/api/config")
    async def get_config():
        """Get current configuration."""
        return {
            "title_template": settings.title_template or PRESET_TEMPLATES[0]["title"],
            "message_template": settings.message_template or PRESET_TEMPLATES[0]["message"],
            "frigate_url": settings.frigate_url,
            "gotify_url": settings.gotify_url,
            "image_compression_enabled": settings.image_compression_enabled,
            "image_max_width": settings.image_max_width,
            "image_max_height": settings.image_max_height,
            "image_quality": settings.image_quality,
            "image_max_size_kb": settings.image_max_size_kb,
        }
    
    @app.post("/api/preview")
    async def preview_template(request: TemplateSaveRequest):
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
    async def save_config(request: TemplateSaveRequest):
        """Save configuration to config directory."""
        try:
            # Use writable config directory (mounted volume)
            config_dir = Path("/app/config")
            config_dir.mkdir(exist_ok=True)
            
            config_file = config_dir / "templates.env"
            
            # Build config content
            config_content = f"""# Template configuration (auto-generated by Web UI)
# Restart the service after changes
TITLE_TEMPLATE={request.title_template}
MESSAGE_TEMPLATE={request.message_template}
"""
            
            # Write config
            config_file.write_text(config_content)
            logger.info(f"Template configuration saved to {config_file}")
            
            return {
                "success": True, 
                "message": "Configuration saved to config/templates.env. Add this to your .env and restart the service to apply."
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
    
    # Serve static files
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    return app
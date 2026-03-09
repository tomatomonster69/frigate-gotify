"""Jinja2 template engine for notification formatting."""

import logging
import re
from typing import Dict, Any, Optional, List
from jinja2 import Environment, BaseLoader, TemplateSyntaxError

logger = logging.getLogger(__name__)


# Default templates
DEFAULT_TITLE_TEMPLATE = "[{{ severity|upper }}] {{ camera }}"
DEFAULT_MESSAGE_TEMPLATE = """{{ camera }} detected {{ object }}{% if sub_label %} ({{ sub_label }}){% endif %} in {{ location }}.
{% if genai_description %}
**AI Summary:** {{ genai_description }}
{% endif %}"""

# Template for object-specific notifications
OBJECT_TEMPLATES = {
    "person": "{{ camera }} detected a person in {{ location }}.{% if genai_description %}\n\n**AI Summary:** {{ genai_description }}{% endif %}",
    "car": "{{ camera }} detected a vehicle{% if sub_label %} ({{ sub_label }}){% endif %} in {{ location }}.{% if genai_description %}\n\n**AI Summary:** {{ genai_description }}{% endif %}",
    "truck": "{{ camera }} detected a truck{% if sub_label %} ({{ sub_label }}){% endif %} in {{ location }}.{% if genai_description %}\n\n**AI Summary:** {{ genai_description }}{% endif %}",
    "dog": "{{ camera }} detected a dog in {{ location }}.{% if genai_description %}\n\n**AI Summary:** {{ genai_description }}{% endif %}",
    "cat": "{{ camera }} detected a cat in {{ location }}.{% if genai_description %}\n\n**AI Summary:** {{ genai_description }}{% endif %}",
}

# Severity-specific templates
SEVERITY_TEMPLATES = {
    "alert": "🚨 ALERT: {{ camera }} detected {{ object }}{% if sub_label %} ({{ sub_label }}){% endif %} in {{ location }}!{% if genai_description %}\n\n**AI Summary:** {{ genai_description }}{% endif %}",
    "detection": "{{ camera }} detected {{ object }}{% if sub_label %} ({{ sub_label }}){% endif %} in {{ location }}.{% if genai_description %}\n\n**AI Summary:** {{ genai_description }}{% endif %}",
}


class TemplateEngine:
    """Jinja2-based template engine for notification formatting."""
    
    def __init__(
        self,
        title_template: Optional[str] = None,
        message_template: Optional[str] = None,
        object_templates: Optional[Dict[str, str]] = None,
        severity_templates: Optional[Dict[str, str]] = None,
        camera_templates: Optional[Dict[str, str]] = None,
    ):
        self.env = Environment(
            loader=BaseLoader(),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        
        # Add custom filters
        self.env.filters["upper"] = str.upper
        self.env.filters["lower"] = str.lower
        self.env.filters["title"] = str.title
        self.env.filters["capitalize"] = self._capitalize_article
        
        # Store templates
        self.title_template = title_template or DEFAULT_TITLE_TEMPLATE
        self.message_template = message_template or DEFAULT_MESSAGE_TEMPLATE
        self.object_templates = {**OBJECT_TEMPLATES, **(object_templates or {})}
        self.severity_templates = {**SEVERITY_TEMPLATES, **(severity_templates or {})}
        self.camera_templates = camera_templates or {}
        
        # Pre-compile templates for performance
        self._compiled = {}
        self._compile_templates()
    
    def _capitalize_article(self, text: str) -> str:
        """Capitalize text with proper article handling."""
        if not text:
            return ""
        vowels = "aeiou"
        if text[0].lower() in vowels:
            return f"an {text}"
        return f"a {text}"
    
    def _compile_templates(self):
        """Pre-compile all templates for better performance."""
        try:
            self._compiled["title"] = self.env.from_string(self.title_template)
            self._compiled["message"] = self.env.from_string(self.message_template)
            
            for key, template in self.object_templates.items():
                self._compiled[f"object_{key}"] = self.env.from_string(template)
            
            for key, template in self.severity_templates.items():
                self._compiled[f"severity_{key}"] = self.env.from_string(template)
            
            for key, template in self.camera_templates.items():
                self._compiled[f"camera_{key}"] = self.env.from_string(template)
                
        except TemplateSyntaxError as e:
            logger.error(f"Template syntax error: {e}")
            raise ValueError(f"Invalid template syntax: {e}")
    
    def _get_template_vars(
        self,
        camera: str,
        object_label: str,
        sub_label: Optional[str],
        location: str,
        severity: str,
        genai_description: Optional[str],
        zones: Optional[List[str]] = None,
        audio: Optional[List[str]] = None,
        timestamp: Optional[str] = None,
        score: Optional[float] = None,
        **extra_vars
    ) -> Dict[str, Any]:
        """Build the template variables dictionary."""
        # Format object with article if needed
        object_display = self._format_object_display(object_label, sub_label)
        
        # Format location
        location_display = self._format_location(location, zones)
        
        return {
            # Basic variables
            "camera": camera,
            "camera_name": camera.replace("_", " ").title(),
            "object": object_label,
            "object_label": object_label,
            "sub_label": sub_label,
            "sublabel": sub_label,  # Alias
            "location": location_display,
            "zone": location_display,  # Alias
            "zones": zones or [],
            "severity": severity,
            "genai_description": genai_description,
            "genai": genai_description,  # Alias
            "ai_summary": genai_description,  # Alias
            
            # Formatted displays
            "object_display": object_display,
            "location_display": location_display,
            
            # Audio
            "audio": audio or [],
            "audio_detected": ", ".join(audio) if audio else None,
            
            # Timing
            "timestamp": timestamp,
            "time": timestamp,
            
            # Score
            "score": score,
            "confidence": f"{score * 100:.0f}%" if score else None,
            
            # Extra
            **extra_vars
        }
    
    def _format_object_display(self, object_label: str, sub_label: Optional[str]) -> str:
        """Format object with sub-label for display."""
        if sub_label:
            return f"{object_label} ({sub_label})"
        return object_label
    
    def _format_location(self, location: str, zones: Optional[List[str]]) -> str:
        """Format location/zone for display."""
        if zones:
            return ", ".join(zones)
        return location.replace("_", " ")
    
    def render_title(
        self,
        camera: str,
        severity: str,
        **kwargs
    ) -> str:
        """Render the notification title."""
        vars = self._get_template_vars(
            camera=camera,
            object_label=kwargs.get("object_label", "object"),
            sub_label=kwargs.get("sub_label"),
            location=kwargs.get("location", "unknown area"),
            severity=severity,
            genai_description=kwargs.get("genai_description"),
            **kwargs
        )
        
        # Check for camera-specific template
        if camera in self.camera_templates:
            template = self._compiled.get(f"camera_{camera}")
            if template:
                return template.render(**vars)
        
        return self._compiled["title"].render(**vars)
    
    def render_message(
        self,
        camera: str,
        object_label: str,
        sub_label: Optional[str],
        location: str,
        severity: str,
        genai_description: Optional[str] = None,
        zones: Optional[List[str]] = None,
        audio: Optional[List[str]] = None,
        timestamp: Optional[str] = None,
        score: Optional[float] = None,
        **kwargs
    ) -> str:
        """Render the notification message.
        
        Priority order for template selection:
        1. Camera-specific template
        2. Object-specific template
        3. Severity-specific template
        4. Default template
        """
        vars = self._get_template_vars(
            camera=camera,
            object_label=object_label,
            sub_label=sub_label,
            location=location,
            severity=severity,
            genai_description=genai_description,
            zones=zones,
            audio=audio,
            timestamp=timestamp,
            score=score,
            **kwargs
        )
        
        # Try camera-specific template first
        if camera in self.camera_templates:
            template = self._compiled.get(f"camera_{camera}")
            if template:
                return template.render(**vars)
        
        # Try object-specific template
        if object_label in self.object_templates:
            template = self._compiled.get(f"object_{object_label}")
            if template:
                return template.render(**vars)
        
        # Try severity-specific template
        if severity in self.severity_templates:
            template = self._compiled.get(f"severity_{severity}")
            if template:
                return template.render(**vars)
        
        # Fall back to default template
        return self._compiled["message"].render(**vars)
    
    def validate_template(self, template_string: str) -> tuple[bool, Optional[str]]:
        """Validate a template string.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            self.env.from_string(template_string)
            return True, None
        except TemplateSyntaxError as e:
            return False, str(e)


def parse_template_config(config_string: str) -> Dict[str, str]:
    """Parse a template configuration string.
    
    Format: "key1:template1;key2:template2"
    Example: "person:Person detected!;car:Vehicle detected!"
    """
    if not config_string:
        return {}
    
    templates = {}
    for part in config_string.split(";"):
        if ":" in part:
            key, template = part.split(":", 1)
            templates[key.strip()] = template.strip()
    
    return templates
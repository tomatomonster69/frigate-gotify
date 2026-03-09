"""Configuration management for frigate-gotify service."""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Frigate Configuration
    frigate_url: str = Field(
        default="http://frigate:5000",
        description="URL of the Frigate NVR server"
    )
    frigate_api_key: Optional[str] = Field(
        default=None,
        description="API key for Frigate (if auth is enabled)"
    )
    frigate_username: Optional[str] = Field(
        default=None,
        description="Username for Frigate authentication"
    )
    frigate_password: Optional[str] = Field(
        default=None,
        description="Password for Frigate authentication"
    )
    
    # Gotify Configuration
    gotify_url: str = Field(
        ...,
        description="URL of the Gotify server"
    )
    gotify_app_token: str = Field(
        ...,
        description="Application token for Gotify"
    )
    
    # SSL Configuration
    verify_ssl: bool = Field(
        default=False,
        description="Whether to verify SSL certificates"
    )
    
    # Polling Configuration
    poll_interval: int = Field(
        default=10,
        description="Interval in seconds between polling for new review events"
    )
    
    # Notification Configuration
    notification_priority: int = Field(
        default=5,
        description="Default priority for Gotify notifications (1-10)"
    )
    include_snapshot: bool = Field(
        default=True,
        description="Whether to include snapshot images in notifications"
    )
    
    # Image Configuration
    snapshot_quality: int = Field(
        default=90,
        description="Snapshot quality from Frigate (1-100)"
    )
    snapshot_format: str = Field(
        default="jpg",
        description="Snapshot format from Frigate (jpg, png, webp)"
    )
    
    # Image Compression Configuration (for Gotify)
    image_compression_enabled: bool = Field(
        default=True,
        description="Enable image compression before sending to Gotify"
    )
    image_max_width: int = Field(
        default=640,
        description="Maximum image width in pixels for notifications"
    )
    image_max_height: int = Field(
        default=480,
        description="Maximum image height in pixels for notifications"
    )
    image_quality: int = Field(
        default=75,
        description="JPEG quality for compressed images (1-100)"
    )
    image_max_size_kb: int = Field(
        default=100,
        description="Maximum image size in KB (approximate)"
    )
    
    # Filter Configuration
    severity_filter: str = Field(
        default="alert,detection",
        description="Comma-separated list of severity levels to notify on"
    )
    camera_filter: str = Field(
        default="all",
        description="Comma-separated list of cameras to monitor, or 'all'"
    )
    
    # Template Configuration
    title_template: Optional[str] = Field(
        default=None,
        description="Jinja2 template for notification title"
    )
    message_template: Optional[str] = Field(
        default=None,
        description="Jinja2 template for notification message"
    )
    object_templates: str = Field(
        default="",
        description="Object-specific templates (format: object:template;object2:template2)"
    )
    severity_templates: str = Field(
        default="",
        description="Severity-specific templates (format: severity:template;severity2:template2)"
    )
    camera_templates: str = Field(
        default="",
        description="Camera-specific templates (format: camera:template;camera2:template2)"
    )
    
    # Debug Configuration
    debug: bool = Field(
        default=False,
        description="Enable debug logging"
    )
    
    class Config:
        env_file = "/app/config/.env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
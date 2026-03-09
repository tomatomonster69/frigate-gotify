"""Gotify API client for sending push notifications with images."""

import logging
from typing import Optional, Dict, Any
import httpx
import base64

from .config import settings

logger = logging.getLogger(__name__)


class GotifyClient:
    """Client for interacting with the Gotify API."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        app_token: Optional[str] = None,
        verify_ssl: Optional[bool] = None,
    ):
        self.base_url = (base_url or settings.gotify_url).rstrip("/")
        self.app_token = app_token or settings.gotify_app_token
        self.verify_ssl = verify_ssl if verify_ssl is not None else settings.verify_ssl
        
        # Build headers with app token
        self.headers = {
            "X-Gotify-Key": self.app_token,
            "Content-Type": "application/json",
        }
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> httpx.Response:
        """Make an HTTP request to the Gotify API."""
        url = f"{self.base_url}{endpoint}"
        
        # Merge headers
        headers = {**self.headers, **kwargs.pop("headers", {})}
        
        async with httpx.AsyncClient(verify=self.verify_ssl, timeout=30.0) as client:
            response = await client.request(
                method,
                url,
                headers=headers,
                **kwargs
            )
            response.raise_for_status()
            return response
    
    async def send_message(
        self,
        title: str,
        message: str,
        priority: Optional[int] = None,
        extras: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send a text message to Gotify.
        
        Args:
            title: Message title
            message: Message content (supports Markdown)
            priority: Message priority (0-10), defaults to settings value
            extras: Extra data for the message
            
        Returns:
            Response from Gotify API
        """
        if priority is None:
            priority = settings.notification_priority
        
        payload = {
            "title": title,
            "message": message,
            "priority": priority,
        }
        
        if extras:
            payload["extras"] = extras
        
        try:
            response = await self._request("POST", "/message", json=payload)
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error sending message to Gotify: {e}")
            raise
    
    async def send_message_with_image_data(
        self,
        title: str,
        message: str,
        image_data: bytes,
        image_format: str = "jpeg",
        priority: Optional[int] = None,
        extras: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send a message with embedded image data (base64).
        
        This ensures remote clients can view images without accessing local Frigate.
        The image is embedded as a base64 data URI in the message.
        
        Gotify image display options:
        - bigImageUrl: Shows large image in notification view
        - bigImage: Uses base64 data URI for embedded images
        
        Args:
            title: Message title
            message: Message content
            image_data: Raw image bytes
            image_format: Image format (jpeg, png, webp)
            priority: Message priority
            extras: Extra data for the message
            
        Returns:
            Response from Gotify API
        """
        if extras is None:
            extras = {}
        
        if priority is None:
            priority = settings.notification_priority
        
        # Encode image as base64
        b64_image = base64.b64encode(image_data).decode("utf-8")
        mime_type = f"image/{image_format}"
        data_uri = f"data:{mime_type};base64,{b64_image}"
        
        # Configure extras for Gotify clients to display images properly
        # client::display controls how the message is rendered
        extras["client::display"] = {
            "contentType": "text/markdown",
        }
        
        # client::notification controls the notification appearance
        # Using bigImageUrl with data URI for large embedded image
        extras["client::notification"] = {
            "bigImageUrl": data_uri,
            "bigImage": data_uri,  # Fallback for some clients
            # Try to make image bigger
            "image": data_uri,
        }
        
        # Also add android-specific extras for better image display
        extras["android"] = {
            "style": "bigPicture",
            "pictureUrl": data_uri,
            "largeImage": data_uri,
        }
        
        # Include image in markdown message as data URI for maximum compatibility
        full_message = f"{message}\n\n![snapshot]({data_uri})"
        
        return await self.send_message(title, full_message, priority, extras)
    
    async def send_message_with_external_image(
        self,
        title: str,
        message: str,
        image_url: str,
        priority: Optional[int] = None,
        extras: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send a message with an external image URL.
        
        Note: This requires the Gotify client to have access to the image URL.
        For remote clients without local network access, use send_message_with_image_data instead.
        
        Args:
            title: Message title
            message: Message content
            image_url: URL to the image
            priority: Message priority
            extras: Extra data for the message
            
        Returns:
            Response from Gotify API
        """
        if extras is None:
            extras = {}
        
        if priority is None:
            priority = settings.notification_priority
        
        # Configure extras for image display
        extras["client::display"] = {
            "contentType": "text/markdown",
        }
        extras["client::notification"] = {
            "bigImageUrl": image_url,
        }
        
        # Include image in markdown message
        full_message = f"{message}\n\n![snapshot]({image_url})"
        
        return await self.send_message(title, full_message, priority, extras)
    
    async def health_check(self) -> bool:
        """Check if Gotify server is reachable.
        
        Returns:
            True if server is healthy, False otherwise
        """
        try:
            # Use the health endpoint (no auth required)
            async with httpx.AsyncClient(verify=self.verify_ssl, timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except httpx.HTTPError:
            return False
"""Frigate NVR API client for fetching review events and snapshots."""

import logging
from typing import Optional, List, Dict, Any
import httpx
from dataclasses import dataclass
from datetime import datetime

from .config import settings

logger = logging.getLogger(__name__)


@dataclass
class ReviewEvent:
    """Represents a Frigate review event."""
    id: str
    camera: str
    start_time: datetime
    end_time: Optional[datetime]
    severity: str
    thumb_path: str
    data: Dict[str, Any]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReviewEvent":
        """Create a ReviewEvent from API response dictionary."""
        return cls(
            id=data["id"],
            camera=data["camera"],
            start_time=datetime.fromtimestamp(data["start_time"]),
            end_time=datetime.fromtimestamp(data["end_time"]) if data.get("end_time") else None,
            severity=data["severity"],
            thumb_path=data.get("thumb_path", ""),
            data=data.get("data", {}),
        )
    
    @property
    def objects(self) -> List[str]:
        """List of detected objects in this review."""
        return self.data.get("objects", [])
    
    @property
    def zones(self) -> List[str]:
        """List of zones involved in this review."""
        return self.data.get("zones", [])
    
    @property
    def audio(self) -> List[str]:
        """List of detected audio in this review."""
        return self.data.get("audio", [])


@dataclass
class Event:
    """Represents a Frigate event."""
    id: str
    camera: str
    label: str
    sub_label: Optional[str]
    start_time: datetime
    end_time: Optional[datetime]
    top_score: float
    zones: List[str]
    has_clip: bool
    has_snapshot: bool
    data: Dict[str, Any]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create an Event from API response dictionary."""
        return cls(
            id=data["id"],
            camera=data["camera"],
            label=data["label"],
            sub_label=data.get("sub_label"),
            start_time=datetime.fromtimestamp(data["start_time"]),
            end_time=datetime.fromtimestamp(data["end_time"]) if data.get("end_time") else None,
            top_score=data.get("top_score", 0),
            zones=data.get("zones", []),
            has_clip=data.get("has_clip", False),
            has_snapshot=data.get("has_snapshot", False),
            data=data.get("data", {}),
        )
    
    @property
    def description(self) -> Optional[str]:
        """Get the GenAI description if available."""
        return self.data.get("description")


class FrigateClient:
    """Client for interacting with the Frigate NVR API."""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        api_key: Optional[str] = None,
        verify_ssl: Optional[bool] = None,
    ):
        self.base_url = (base_url or settings.frigate_url).rstrip("/")
        self.username = username or settings.frigate_username
        self.password = password or settings.frigate_password
        self.api_key = api_key or settings.frigate_api_key
        self.verify_ssl = verify_ssl if verify_ssl is not None else settings.verify_ssl
        
        # Build headers
        self.headers = {}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
        
        # Build auth
        self.auth = None
        if self.username and self.password:
            self.auth = (self.username, self.password)
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> httpx.Response:
        """Make an HTTP request to the Frigate API."""
        url = f"{self.base_url}{endpoint}"
        
        # Merge headers
        headers = {**self.headers, **kwargs.pop("headers", {})}
        
        async with httpx.AsyncClient(verify=self.verify_ssl) as client:
            response = await client.request(
                method,
                url,
                headers=headers,
                auth=self.auth,
                **kwargs
            )
            response.raise_for_status()
            return response
    
    async def get_review_events(
        self,
        cameras: str = "all",
        severity: str = "alert,detection",
        reviewed: bool = False,
        limit: int = 100,
    ) -> List[ReviewEvent]:
        """Fetch unreviewed review events from Frigate.
        
        Args:
            cameras: Comma-separated camera names or 'all'
            severity: Comma-separated severity levels (alert, detection)
            reviewed: Whether to include reviewed events
            limit: Maximum number of events to return
            
        Returns:
            List of ReviewEvent objects
        """
        params = {
            "cameras": cameras,
            "reviewed": "1" if reviewed else "0",
            "limit": limit,
        }
        
        # Note: severity filtering may need to be done client-side
        # depending on API version
        
        try:
            response = await self._request("GET", "/api/review", params=params)
            events = response.json()
            
            # Filter by severity if needed
            severity_list = [s.strip() for s in severity.split(",")]
            if severity_list and "all" not in severity_list:
                events = [e for e in events if e.get("severity") in severity_list]
            
            return [ReviewEvent.from_dict(e) for e in events]
        except httpx.HTTPError as e:
            logger.error(f"Error fetching review events: {e}")
            return []
    
    async def get_review_event(self, review_id: str) -> Optional[ReviewEvent]:
        """Fetch a specific review event by ID.
        
        Args:
            review_id: The ID of the review event
            
        Returns:
            ReviewEvent or None if not found
        """
        try:
            response = await self._request("GET", f"/api/review/{review_id}")
            data = response.json()
            return ReviewEvent.from_dict(data)
        except httpx.HTTPError as e:
            logger.error(f"Error fetching review event {review_id}: {e}")
            return None
    
    async def get_events(
        self,
        camera: str = "all",
        label: str = "all",
        limit: int = 100,
        in_progress: bool = False,
        has_snapshot: bool = True,
    ) -> List[Event]:
        """Fetch events from Frigate.
        
        Args:
            camera: Camera name or 'all'
            label: Object label to filter by
            limit: Maximum number of events to return
            in_progress: Include in-progress events
            has_snapshot: Only include events with snapshots
            
        Returns:
            List of Event objects
        """
        params = {
            "cameras": camera,
            "limit": limit,
            "in_progress": "1" if in_progress else "0",
            "has_snapshot": "1" if has_snapshot else "0",
        }
        
        try:
            response = await self._request("GET", "/api/events", params=params)
            events = response.json()
            return [Event.from_dict(e) for e in events]
        except httpx.HTTPError as e:
            logger.error(f"Error fetching events: {e}")
            return []
    
    async def get_event(self, event_id: str) -> Optional[Event]:
        """Fetch a specific event by ID.
        
        Args:
            event_id: The ID of the event
            
        Returns:
            Event or None if not found
        """
        try:
            response = await self._request("GET", f"/api/events/{event_id}")
            data = response.json()
            return Event.from_dict(data)
        except httpx.HTTPError as e:
            logger.error(f"Error fetching event {event_id}: {e}")
            return None
    
    async def get_snapshot(
        self,
        event_id: str,
        format: str = "jpg",
        quality: int = 70,
    ) -> Optional[bytes]:
        """Fetch the snapshot image for an event.
        
        Args:
            event_id: The ID of the event
            format: Image format (jpg, png, webp)
            quality: Image quality (1-100)
            
        Returns:
            Image bytes or None if not available
        """
        try:
            response = await self._request(
                "GET",
                f"/api/events/{event_id}/snapshot.{format}",
                params={"quality": quality},
            )
            return response.content
        except httpx.HTTPError as e:
            logger.error(f"Error fetching snapshot for event {event_id}: {e}")
            return None
    
    async def get_review_thumbnail(
        self,
        review_id: str,
        format: str = "jpg",
    ) -> Optional[bytes]:
        """Fetch the thumbnail image for a review event.
        
        Args:
            review_id: The ID of the review event
            format: Image format (jpg, png)
            
        Returns:
            Image bytes or None if not available
        """
        try:
            response = await self._request(
                "GET",
                f"/api/review/{review_id}/thumbnail.{format}",
            )
            return response.content
        except httpx.HTTPError as e:
            logger.error(f"Error fetching thumbnail for review {review_id}: {e}")
            return None
    
    async def get_clip_url(self, event_id: str) -> str:
        """Get the URL for an event's video clip.
        
        Args:
            event_id: The ID of the event
            
        Returns:
            URL string for the clip
        """
        return f"{self.base_url}/api/events/{event_id}/clip.mp4"
    
    async def get_clip(self, event_id: str) -> Optional[bytes]:
        """Fetch the video clip for an event.
        
        Args:
            event_id: The ID of the event
            
        Returns:
            Video bytes or None if not available
        """
        try:
            response = await self._request(
                "GET",
                f"/api/events/{event_id}/clip.mp4",
            )
            return response.content
        except httpx.HTTPError as e:
            logger.error(f"Error fetching clip for event {event_id}: {e}")
            return None
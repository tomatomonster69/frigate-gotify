"""Main service for frigate-gotify notification bridge."""

import asyncio
import logging
import signal
import sys
from datetime import datetime
from typing import Set, Optional

from .config import settings
from .frigate_client import FrigateClient, ReviewEvent, Event
from .gotify_client import GotifyClient

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


class FrigateGotifyBridge:
    """Bridge service between Frigate NVR and Gotify notifications."""
    
    def __init__(self):
        self.frigate = FrigateClient()
        self.gotify = GotifyClient()
        self.running = False
        self.processed_reviews: Set[str] = set()
        
    async def start(self):
        """Start the bridge service."""
        logger.info("Starting Frigate-Gotify bridge...")
        logger.info(f"Frigate URL: {settings.frigate_url}")
        logger.info(f"Gotify URL: {settings.gotify_url}")
        logger.info(f"Poll interval: {settings.poll_interval}s")
        logger.info(f"Severity filter: {settings.severity_filter}")
        logger.info(f"Camera filter: {settings.camera_filter}")
        
        # Health checks
        if not await self.gotify.health_check():
            logger.warning("Gotify health check failed, but continuing anyway...")
        
        self.running = True
        logger.info("Bridge service started successfully")
        
        # Main loop
        while self.running:
            try:
                await self.poll_events()
            except Exception as e:
                logger.error(f"Error in polling loop: {e}", exc_info=True)
            
            await asyncio.sleep(settings.poll_interval)
    
    def stop(self):
        """Stop the bridge service."""
        logger.info("Stopping Frigate-Gotify bridge...")
        self.running = False
    
    async def poll_events(self):
        """Poll for new review events and send notifications."""
        # Get unreviewed review events
        reviews = await self.frigate.get_review_events(
            cameras=settings.camera_filter,
            severity=settings.severity_filter,
            reviewed=False,
            limit=20,
        )
        
        logger.debug(f"Found {len(reviews)} unreviewed events")
        
        for review in reviews:
            if review.id in self.processed_reviews:
                continue
            
            logger.info(f"Processing review: {review.id} - {review.camera} - {review.severity}")
            await self.process_review(review)
            self.processed_reviews.add(review.id)
            
            # Clean up old IDs to prevent memory bloat
            if len(self.processed_reviews) > 1000:
                self.processed_reviews = set(list(self.processed_reviews)[-500:])
    
    async def process_review(self, review: ReviewEvent):
        """Process a single review event and send notification.
        
        Args:
            review: The review event to process
        """
        try:
            # Get related events for this review to find GenAI descriptions
            related_events = await self.frigate.get_events(
                camera=review.camera,
                limit=10,
            )
            
            # Find the best event with a description and snapshot
            best_event: Optional[Event] = None
            for event in related_events:
                # Check if event is within review timeframe
                if event.start_time >= review.start_time:
                    if event.has_snapshot:
                        best_event = event
                        if event.description:  # Prefer events with GenAI description
                            break
            
            # Build notification message
            title = f"[{review.severity.upper()}] {review.camera}"
            
            # Build message content
            message_parts = []
            
            # Add GenAI description if available
            if best_event and best_event.description:
                message_parts.append(f"**Description:** {best_event.description}")
            
            # Add detected objects
            if review.objects:
                objects_str = ", ".join(review.objects)
                message_parts.append(f"**Objects:** {objects_str}")
            
            # Add zones
            if review.zones:
                zones_str = ", ".join(review.zones)
                message_parts.append(f"**Zones:** {zones_str}")
            
            # Add audio detections
            if review.audio:
                audio_str = ", ".join(review.audio)
                message_parts.append(f"**Audio:** {audio_str}")
            
            # Add timestamp
            timestamp = review.start_time.strftime("%Y-%m-%d %H:%M:%S")
            message_parts.append(f"**Time:** {timestamp}")
            
            message = "\n".join(message_parts)
            
            # Get snapshot image if available
            if settings.include_snapshot and best_event and best_event.has_snapshot:
                image_data = await self.frigate.get_snapshot(best_event.id)
                
                if image_data:
                    await self.gotify.send_message_with_image_data(
                        title=title,
                        message=message,
                        image_data=image_data,
                        image_format="jpeg",
                        priority=settings.notification_priority,
                    )
                    logger.info(f"Sent notification with image for review {review.id}")
                else:
                    # Send without image
                    await self.gotify.send_message(title=title, message=message)
                    logger.info(f"Sent notification (no image) for review {review.id}")
            else:
                # Send without image
                await self.gotify.send_message(title=title, message=message)
                logger.info(f"Sent notification (no snapshot available) for review {review.id}")
                
        except Exception as e:
            logger.error(f"Error processing review {review.id}: {e}", exc_info=True)


async def main():
    """Main entry point."""
    bridge = FrigateGotifyBridge()
    
    # Handle shutdown signals
    loop = asyncio.get_event_loop()
    
    def shutdown_handler():
        logger.info("Shutdown signal received")
        bridge.stop()
    
    # Register signal handlers
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown_handler)
    
    try:
        await bridge.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        bridge.stop()
        logger.info("Bridge service stopped")


if __name__ == "__main__":
    asyncio.run(main())
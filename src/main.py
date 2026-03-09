"""Main service for frigate-gotify notification bridge."""

import asyncio
import logging
import signal
import sys
import threading
from datetime import datetime
from typing import Set, Optional, Dict, Any

import uvicorn
from .config import settings
from .frigate_client import FrigateClient, ReviewEvent, Event
from .gotify_client import GotifyClient
from .template_engine import TemplateEngine, parse_template_config
from .webui import create_app

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
        
        # Initialize template engine
        self.template_engine = TemplateEngine(
            title_template=settings.title_template,
            message_template=settings.message_template,
            object_templates=parse_template_config(settings.object_templates),
            severity_templates=parse_template_config(settings.severity_templates),
            camera_templates=parse_template_config(settings.camera_templates),
        )
        
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
            
            # Extract template data
            object_label = review.objects[0] if review.objects else "unknown"
            sub_label = best_event.sub_label if best_event else None
            genai_description = best_event.description if best_event else None
            zones = review.zones
            audio = review.audio
            timestamp = review.start_time.strftime("%Y-%m-%d %H:%M:%S")
            score = best_event.top_score if best_event else None
            
            # Get location - use zones if available, otherwise use camera name
            location = ", ".join(zones) if zones else review.camera.replace("_", " ")
            
            # Render title using template engine
            title = self.template_engine.render_title(
                camera=review.camera,
                severity=review.severity,
                object_label=object_label,
                sub_label=sub_label,
                location=location,
                genai_description=genai_description,
                zones=zones,
                audio=audio,
                timestamp=timestamp,
                score=score,
            )
            
            # Render message using template engine
            message = self.template_engine.render_message(
                camera=review.camera,
                object_label=object_label,
                sub_label=sub_label,
                location=location,
                severity=review.severity,
                genai_description=genai_description,
                zones=zones,
                audio=audio,
                timestamp=timestamp,
                score=score,
            )
            
            # Get snapshot image if available
            if settings.include_snapshot and best_event and best_event.has_snapshot:
                image_data = await self.frigate.get_snapshot(
                    best_event.id,
                    format=settings.snapshot_format,
                    quality=settings.snapshot_quality,
                )
                
                if image_data:
                    await self.gotify.send_message_with_image_data(
                        title=title,
                        message=message,
                        image_data=image_data,
                        image_format=settings.snapshot_format,
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


def run_web_server():
    """Run the web UI server in a separate thread."""
    app = create_app()
    logger.info("Starting Web UI on http://0.0.0.0:80")
    uvicorn.run(app, host="0.0.0.0", port=80, log_level="warning")


async def main():
    """Main entry point."""
    # Start web UI in a separate thread
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    logger.info("Web UI thread started")
    
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

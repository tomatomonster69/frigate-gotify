"""Image compression utility for optimizing images before sending to Gotify."""

import logging
from io import BytesIO
from typing import Optional, Tuple
from PIL import Image

from .config import settings

logger = logging.getLogger(__name__)


class ImageCompressor:
    """Compresses images for mobile push notifications."""
    
    def __init__(
        self,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
        quality: Optional[int] = None,
        max_size_kb: Optional[int] = None,
    ):
        self.max_width = max_width or settings.image_max_width
        self.max_height = max_height or settings.image_max_height
        self.quality = quality or settings.image_quality
        self.max_size_kb = max_size_kb or settings.image_max_size_kb
        
    def compress(
        self,
        image_data: bytes,
        format: str = "JPEG",
    ) -> Tuple[bytes, str]:
        """Compress image data to meet size constraints.
        
        Args:
            image_data: Raw image bytes (any format Pillow supports)
            format: Output format (JPEG, PNG, WEBP)
            
        Returns:
            Tuple of (compressed_image_bytes, format)
        """
        try:
            # Open the image
            img = Image.open(BytesIO(image_data))
            
            # Convert to RGB if necessary (for JPEG)
            if format.upper() == "JPEG" and img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # Get original dimensions
            original_width, original_height = img.size
            
            # Calculate new dimensions maintaining aspect ratio
            new_width, new_height = self._calculate_new_dimensions(
                original_width, original_height
            )
            
            # Resize if needed
            if new_width != original_width or new_height != original_height:
                logger.debug(f"Resizing image from {original_width}x{original_height} to {new_width}x{new_height}")
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Compress with iterative quality reduction
            compressed_data, final_quality = self._compress_with_size_limit(
                img, format, self.quality, self.max_size_kb * 1024
            )
            
            logger.info(
                f"Compressed image: {original_width}x{original_height} -> "
                f"{new_width}x{new_height}, quality={final_quality}, "
                f"size={len(compressed_data) / 1024:.1f}KB"
            )
            
            return compressed_data, format.lower()
            
        except Exception as e:
            logger.error(f"Error compressing image: {e}")
            # Return original data if compression fails
            return image_data, format.lower()
    
    def _calculate_new_dimensions(
        self,
        width: int,
        height: int,
    ) -> Tuple[int, int]:
        """Calculate new dimensions maintaining aspect ratio."""
        if width <= self.max_width and height <= self.max_height:
            return width, height
        
        # Calculate scaling factor
        width_ratio = self.max_width / width
        height_ratio = self.max_height / height
        scale_factor = min(width_ratio, height_ratio)
        
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        
        return new_width, new_height
    
    def _compress_with_size_limit(
        self,
        img: Image.Image,
        format: str,
        initial_quality: int,
        max_size_bytes: int,
        min_quality: int = 10,
    ) -> Tuple[bytes, int]:
        """Compress image with iterative quality reduction to meet size limit.
        
        Args:
            img: PIL Image object
            format: Output format
            initial_quality: Starting quality (1-100)
            max_size_bytes: Maximum output size in bytes
            min_quality: Minimum quality to try before giving up
            
        Returns:
            Tuple of (compressed_bytes, final_quality)
        """
        quality = initial_quality
        
        while quality >= min_quality:
            buffer = BytesIO()
            
            # Save with current quality
            save_kwargs = {"format": format}
            if format.upper() == "JPEG":
                save_kwargs["quality"] = quality
                save_kwargs["optimize"] = True
            elif format.upper() == "WEBP":
                save_kwargs["quality"] = quality
            
            img.save(buffer, **save_kwargs)
            data = buffer.getvalue()
            
            # Check if size is acceptable
            if len(data) <= max_size_bytes:
                return data, quality
            
            # Reduce quality for next iteration
            quality -= 10
        
        # If we still can't meet size limit, return the smallest version
        logger.warning(
            f"Could not compress image to under {max_size_bytes / 1024:.0f}KB, "
            f"returning at quality {min_quality}"
        )
        
        buffer = BytesIO()
        img.save(buffer, format=format, quality=min_quality, optimize=True)
        return buffer.getvalue(), min_quality
    
    def get_image_info(self, image_data: bytes) -> dict:
        """Get information about an image without fully decoding it.
        
        Args:
            image_data: Raw image bytes
            
        Returns:
            Dictionary with image info
        """
        try:
            img = Image.open(BytesIO(image_data))
            return {
                "width": img.width,
                "height": img.height,
                "format": img.format,
                "mode": img.mode,
                "size_bytes": len(image_data),
                "size_kb": len(image_data) / 1024,
            }
        except Exception as e:
            return {"error": str(e)}


def compress_image(
    image_data: bytes,
    max_width: int = 640,
    max_height: int = 480,
    quality: int = 75,
    max_size_kb: int = 100,
) -> Tuple[bytes, str]:
    """Convenience function to compress an image.
    
    Args:
        image_data: Raw image bytes
        max_width: Maximum width in pixels
        max_height: Maximum height in pixels
        quality: JPEG quality (1-100)
        max_size_kb: Maximum output size in KB
        
    Returns:
        Tuple of (compressed_bytes, format)
    """
    compressor = ImageCompressor(
        max_width=max_width,
        max_height=max_height,
        quality=quality,
        max_size_kb=max_size_kb,
    )
    return compressor.compress(image_data)
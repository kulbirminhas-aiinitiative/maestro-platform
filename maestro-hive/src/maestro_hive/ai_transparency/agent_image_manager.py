"""
Agent Image Manager Module - MD-2792

Manages AI agent images and avatars for consistent visual identity.
Ensures professional, accessible images across the platform.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import hashlib
import json
import logging
import os
import re
import urllib.parse

logger = logging.getLogger(__name__)


class ImageFormat(Enum):
    """Supported image formats."""
    PNG = "png"
    JPG = "jpg"
    JPEG = "jpeg"
    SVG = "svg"
    WEBP = "webp"


class ImageSize(Enum):
    """Standard image sizes."""
    THUMBNAIL = (32, 32)
    SMALL = (64, 64)
    MEDIUM = (128, 128)
    LARGE = (256, 256)
    EXTRA_LARGE = (512, 512)


class ImageStyle(Enum):
    """Agent image visual styles."""
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    TECHNICAL = "technical"
    MINIMAL = "minimal"
    ABSTRACT = "abstract"


@dataclass
class ImageConfig:
    """
    Configuration for agent images.

    Defines visual identity standards and image processing settings.
    """
    # Image sources
    base_path: str = "/images/agents"
    cdn_url: Optional[str] = None
    fallback_url: str = "/images/default-agent.png"

    # Sizing
    default_size: ImageSize = ImageSize.MEDIUM
    allowed_sizes: List[ImageSize] = field(default_factory=lambda: list(ImageSize))

    # Format preferences
    preferred_format: ImageFormat = ImageFormat.PNG
    allowed_formats: List[ImageFormat] = field(default_factory=lambda: list(ImageFormat))

    # Style guidelines
    style: ImageStyle = ImageStyle.PROFESSIONAL
    background_color: str = "#f3f4f6"  # Light gray
    accent_color: str = "#6366f1"  # Indigo

    # Quality settings
    quality: int = 90  # JPEG quality (1-100)
    optimize: bool = True

    # Accessibility
    require_alt_text: bool = True
    default_alt_text: str = "AI Assistant Avatar"

    # Caching
    cache_ttl_seconds: int = 86400  # 24 hours
    cache_enabled: bool = True

    # Validation
    max_file_size_kb: int = 512
    min_dimensions: Tuple[int, int] = (32, 32)
    max_dimensions: Tuple[int, int] = (1024, 1024)

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "base_path": self.base_path,
            "cdn_url": self.cdn_url,
            "fallback_url": self.fallback_url,
            "default_size": self.default_size.name,
            "allowed_sizes": [s.name for s in self.allowed_sizes],
            "preferred_format": self.preferred_format.value,
            "allowed_formats": [f.value for f in self.allowed_formats],
            "style": self.style.value,
            "background_color": self.background_color,
            "accent_color": self.accent_color,
            "quality": self.quality,
            "optimize": self.optimize,
            "require_alt_text": self.require_alt_text,
            "default_alt_text": self.default_alt_text,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "cache_enabled": self.cache_enabled,
            "max_file_size_kb": self.max_file_size_kb,
            "min_dimensions": self.min_dimensions,
            "max_dimensions": self.max_dimensions,
        }


@dataclass
class AgentImage:
    """
    Represents an agent's image/avatar.

    Contains all image variants and metadata for an agent.
    """
    # Identity
    agent_id: str
    image_id: str

    # Primary image
    url: str
    format: ImageFormat
    width: int
    height: int

    # Variants
    variants: Dict[str, str] = field(default_factory=dict)  # size_name -> url

    # Metadata
    alt_text: str = "AI Assistant"
    description: Optional[str] = None
    style: ImageStyle = ImageStyle.PROFESSIONAL
    background_color: Optional[str] = None

    # File info
    file_size_bytes: Optional[int] = None
    content_hash: Optional[str] = None

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def get_url(self, size: Optional[ImageSize] = None) -> str:
        """
        Get image URL for specified size.

        Args:
            size: Desired image size, None for default

        Returns:
            Image URL
        """
        if size and size.name in self.variants:
            return self.variants[size.name]
        return self.url

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "image_id": self.image_id,
            "url": self.url,
            "format": self.format.value,
            "width": self.width,
            "height": self.height,
            "variants": self.variants,
            "alt_text": self.alt_text,
            "description": self.description,
            "style": self.style.value,
            "background_color": self.background_color,
            "file_size_bytes": self.file_size_bytes,
            "content_hash": self.content_hash,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def to_html_img(
        self,
        size: Optional[ImageSize] = None,
        css_class: Optional[str] = None
    ) -> str:
        """
        Generate HTML img tag.

        Args:
            size: Image size variant
            css_class: CSS class to apply

        Returns:
            HTML img tag string
        """
        url = self.get_url(size)
        target_size = size or ImageSize.MEDIUM
        w, h = target_size.value

        class_attr = f' class="{css_class}"' if css_class else ""
        return f'<img src="{url}" alt="{self.alt_text}" width="{w}" height="{h}"{class_attr} />'


class AgentImageManager:
    """
    Manager for AI agent images and avatars.

    Handles image storage, retrieval, validation, and URL generation
    with support for multiple sizes and formats.
    """

    def __init__(self, config: Optional[ImageConfig] = None):
        """
        Initialize the image manager.

        Args:
            config: Image configuration
        """
        self.config = config or ImageConfig()
        self._images: Dict[str, AgentImage] = {}
        self._cache: Dict[str, Tuple[str, datetime]] = {}

    def register_image(
        self,
        agent_id: str,
        url: str,
        format: ImageFormat = ImageFormat.PNG,
        width: int = 128,
        height: int = 128,
        alt_text: Optional[str] = None,
        variants: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> AgentImage:
        """
        Register an image for an agent.

        Args:
            agent_id: Agent identifier
            url: Primary image URL
            format: Image format
            width: Image width
            height: Image height
            alt_text: Alt text for accessibility
            variants: Size variants (size_name -> url)
            **kwargs: Additional image properties

        Returns:
            Created AgentImage
        """
        image_id = f"img_{hashlib.md5(f'{agent_id}_{url}'.encode()).hexdigest()[:12]}"

        image = AgentImage(
            agent_id=agent_id,
            image_id=image_id,
            url=url,
            format=format,
            width=width,
            height=height,
            alt_text=alt_text or self.config.default_alt_text,
            variants=variants or {},
            **kwargs
        )

        self._images[agent_id] = image
        logger.info(f"Registered image for agent {agent_id}: {image_id}")
        return image

    def get_image(self, agent_id: str) -> Optional[AgentImage]:
        """
        Get image for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            AgentImage if found, None otherwise
        """
        return self._images.get(agent_id)

    def get_url(
        self,
        agent_id: str,
        size: Optional[ImageSize] = None,
        use_cdn: bool = True
    ) -> str:
        """
        Get image URL for an agent.

        Args:
            agent_id: Agent identifier
            size: Desired image size
            use_cdn: Whether to use CDN URL if available

        Returns:
            Image URL (fallback if agent not found)
        """
        image = self._images.get(agent_id)

        if not image:
            return self._get_fallback_url(size)

        url = image.get_url(size)

        # Apply CDN if configured and requested
        if use_cdn and self.config.cdn_url:
            url = self._apply_cdn(url)

        return url

    def get_avatar_html(
        self,
        agent_id: str,
        size: ImageSize = ImageSize.MEDIUM,
        css_class: str = "agent-avatar",
        include_badge: bool = True
    ) -> str:
        """
        Generate HTML for agent avatar with optional AI badge.

        Args:
            agent_id: Agent identifier
            size: Image size
            css_class: CSS class for styling
            include_badge: Whether to include AI indicator badge

        Returns:
            HTML string for avatar display
        """
        image = self._images.get(agent_id)
        url = self.get_url(agent_id, size)
        w, h = size.value
        alt = image.alt_text if image else self.config.default_alt_text

        avatar_html = f'''
        <div class="agent-avatar-container" style="position: relative; display: inline-block;">
            <img src="{url}" alt="{alt}" width="{w}" height="{h}" class="{css_class}" />
        '''

        if include_badge:
            avatar_html += '''
            <span class="ai-badge" style="
                position: absolute;
                bottom: -4px;
                right: -4px;
                background: #6366f1;
                color: white;
                font-size: 10px;
                padding: 2px 4px;
                border-radius: 4px;
                font-weight: bold;
            ">AI</span>
            '''

        avatar_html += '</div>'
        return avatar_html.strip()

    def generate_initials_avatar(
        self,
        agent_id: str,
        name: str,
        background_color: Optional[str] = None,
        text_color: str = "#ffffff"
    ) -> str:
        """
        Generate SVG initials-based avatar.

        Args:
            agent_id: Agent identifier
            name: Agent name for initials
            background_color: Background color
            text_color: Text color

        Returns:
            SVG data URL
        """
        # Extract initials (max 2 characters)
        words = name.split()
        if len(words) >= 2:
            initials = words[0][0].upper() + words[1][0].upper()
        else:
            initials = name[:2].upper()

        bg = background_color or self.config.accent_color

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
            <rect width="100" height="100" fill="{bg}" rx="10"/>
            <text x="50" y="55" text-anchor="middle" dominant-baseline="middle"
                  font-family="system-ui, -apple-system, sans-serif"
                  font-size="40" font-weight="bold" fill="{text_color}">
                {initials}
            </text>
        </svg>'''

        # Convert to data URL
        encoded = urllib.parse.quote(svg.strip())
        return f"data:image/svg+xml,{encoded}"

    def validate_image(
        self,
        url: str,
        file_size_bytes: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate image against configuration rules.

        Args:
            url: Image URL
            file_size_bytes: File size if known
            width: Image width if known
            height: Image height if known

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check URL format
        if not url or not isinstance(url, str):
            errors.append("Invalid URL")
            return False, errors

        # Check format from URL
        ext = url.split('.')[-1].lower() if '.' in url else None
        if ext:
            try:
                img_format = ImageFormat(ext)
                if img_format not in self.config.allowed_formats:
                    errors.append(f"Format '{ext}' not allowed")
            except ValueError:
                if not url.startswith("data:"):  # Allow data URLs
                    errors.append(f"Unknown format '{ext}'")

        # Check file size
        if file_size_bytes:
            max_bytes = self.config.max_file_size_kb * 1024
            if file_size_bytes > max_bytes:
                errors.append(
                    f"File size {file_size_bytes} exceeds limit {max_bytes}"
                )

        # Check dimensions
        if width and height:
            min_w, min_h = self.config.min_dimensions
            max_w, max_h = self.config.max_dimensions

            if width < min_w or height < min_h:
                errors.append(
                    f"Dimensions {width}x{height} below minimum {min_w}x{min_h}"
                )
            if width > max_w or height > max_h:
                errors.append(
                    f"Dimensions {width}x{height} exceed maximum {max_w}x{max_h}"
                )

        return len(errors) == 0, errors

    def create_placeholder(
        self,
        agent_id: str,
        name: str = "AI Agent"
    ) -> AgentImage:
        """
        Create a placeholder image for an agent.

        Args:
            agent_id: Agent identifier
            name: Agent name for initials

        Returns:
            AgentImage with placeholder
        """
        svg_url = self.generate_initials_avatar(agent_id, name)

        return self.register_image(
            agent_id=agent_id,
            url=svg_url,
            format=ImageFormat.SVG,
            width=128,
            height=128,
            alt_text=f"{name} Avatar",
            description=f"Auto-generated avatar for {name}"
        )

    def update_image(
        self,
        agent_id: str,
        url: Optional[str] = None,
        alt_text: Optional[str] = None,
        **kwargs
    ) -> Optional[AgentImage]:
        """
        Update an agent's image.

        Args:
            agent_id: Agent identifier
            url: New URL
            alt_text: New alt text
            **kwargs: Additional properties

        Returns:
            Updated AgentImage if found
        """
        image = self._images.get(agent_id)
        if not image:
            return None

        if url:
            image.url = url
        if alt_text:
            image.alt_text = alt_text

        for key, value in kwargs.items():
            if hasattr(image, key):
                setattr(image, key, value)

        image.updated_at = datetime.utcnow()
        return image

    def remove_image(self, agent_id: str) -> bool:
        """
        Remove an agent's image.

        Args:
            agent_id: Agent identifier

        Returns:
            True if removed, False if not found
        """
        if agent_id in self._images:
            del self._images[agent_id]
            return True
        return False

    def list_all(self) -> List[AgentImage]:
        """Get all registered images."""
        return list(self._images.values())

    def get_statistics(self) -> Dict[str, Any]:
        """Get image statistics."""
        by_format = {}
        by_style = {}
        total_size = 0

        for image in self._images.values():
            # By format
            f = image.format.value
            by_format[f] = by_format.get(f, 0) + 1

            # By style
            s = image.style.value
            by_style[s] = by_style.get(s, 0) + 1

            # Total size
            if image.file_size_bytes:
                total_size += image.file_size_bytes

        return {
            "total_images": len(self._images),
            "by_format": by_format,
            "by_style": by_style,
            "total_size_bytes": total_size,
            "cdn_enabled": self.config.cdn_url is not None,
        }

    def _get_fallback_url(self, size: Optional[ImageSize] = None) -> str:
        """Get fallback URL for missing images."""
        base = self.config.fallback_url

        if size and self.config.cdn_url:
            # Add size parameter to CDN URL
            w, h = size.value
            return f"{self.config.cdn_url}{base}?w={w}&h={h}"

        return base

    def _apply_cdn(self, url: str) -> str:
        """Apply CDN prefix to URL."""
        if not self.config.cdn_url:
            return url

        # Skip if already absolute URL or data URL
        if url.startswith(("http://", "https://", "data:")):
            return url

        return f"{self.config.cdn_url.rstrip('/')}/{url.lstrip('/')}"


# Default manager instance
_default_manager: Optional[AgentImageManager] = None


def get_manager() -> AgentImageManager:
    """Get the default image manager instance."""
    global _default_manager
    if _default_manager is None:
        _default_manager = AgentImageManager()
    return _default_manager


def set_manager(manager: AgentImageManager) -> None:
    """Set the default image manager instance."""
    global _default_manager
    _default_manager = manager

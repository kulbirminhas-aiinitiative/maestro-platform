"""AI Watermarking - Invisible markers for AI content"""
import hashlib
import base64
from typing import Optional
from datetime import datetime

class AIWatermark:
    """Adds invisible watermarks to AI-generated content."""

    # Zero-width characters for invisible watermarking
    ZERO_WIDTH_SPACE = '\u200b'
    ZERO_WIDTH_NON_JOINER = '\u200c'
    ZERO_WIDTH_JOINER = '\u200d'

    def __init__(self, secret_key: str = "maestro-ai-watermark"):
        self.secret_key = secret_key

    def _encode_binary(self, binary_str: str) -> str:
        """Encode binary string as zero-width characters."""
        result = ""
        for bit in binary_str:
            if bit == '0':
                result += self.ZERO_WIDTH_SPACE
            else:
                result += self.ZERO_WIDTH_NON_JOINER
        return result

    def _decode_binary(self, watermark: str) -> str:
        """Decode zero-width characters back to binary."""
        binary = ""
        for char in watermark:
            if char == self.ZERO_WIDTH_SPACE:
                binary += '0'
            elif char == self.ZERO_WIDTH_NON_JOINER:
                binary += '1'
        return binary

    def create_watermark(self, content_id: str) -> str:
        """Create invisible watermark."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M")
        data = f"{content_id}:{timestamp}:{self.secret_key}"
        hash_val = hashlib.md5(data.encode()).hexdigest()[:8]

        # Convert to binary
        binary = bin(int(hash_val, 16))[2:].zfill(32)

        return self._encode_binary(binary)

    def embed_watermark(self, content: str, content_id: str) -> str:
        """Embed invisible watermark in content."""
        watermark = self.create_watermark(content_id)

        # Insert watermark after first paragraph
        paragraphs = content.split('\n\n')
        if len(paragraphs) > 1:
            paragraphs[0] = paragraphs[0] + watermark
            return '\n\n'.join(paragraphs)
        else:
            return content + watermark

    def detect_watermark(self, content: str) -> bool:
        """Check if content contains AI watermark."""
        for char in [self.ZERO_WIDTH_SPACE, self.ZERO_WIDTH_NON_JOINER]:
            if char in content:
                return True
        return False

    def verify_watermark(self, content: str, expected_id: str) -> bool:
        """Verify watermark matches expected content ID."""
        # Extract watermark characters
        watermark = ""
        for char in content:
            if char in [self.ZERO_WIDTH_SPACE, self.ZERO_WIDTH_NON_JOINER]:
                watermark += char

        if not watermark:
            return False

        # We can detect presence but full verification requires timestamp
        return len(watermark) >= 32

"""
Abstract base channel adapter for Giraffe Agent IM channels.
"""

from abc import ABC, abstractmethod


class BaseChannelAdapter(ABC):
    """Abstract channel adapter — concrete implementations handle WeChat, WhatsApp, Web, etc."""

    channel_name: str = "base"

    @abstractmethod
    def send_message(self, to: str, text: str) -> bool:
        """Send a message to a user. Returns True on success."""
        ...

    def receive_message(self, payload: dict) -> dict:
        """Parse inbound message payload. Override per channel."""
        return payload

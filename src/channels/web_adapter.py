"""
Web fallback channel adapter — mock mode prints to console.
Used when WeChat / WhatsApp are unavailable.
"""

from src.channels.base import BaseChannelAdapter


class WebAdapter(BaseChannelAdapter):
    """Web fallback channel adapter for Giraffe Agent supplier workspace."""

    channel_name = "web"

    def __init__(self, mock: bool = True):
        self.mock = mock

    def send_message(self, to: str, text: str) -> bool:
        if self.mock:
            print(f"[Web MOCK → {to}]\n{text}\n")
            return True
        # Production: push via WebSocket / SSE
        raise NotImplementedError("Web production push not implemented in MVP.")

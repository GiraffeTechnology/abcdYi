"""
WhatsApp channel adapter — mock mode prints to console; production mode requires credentials.
"""

from src.channels.base import BaseChannelAdapter


class WhatsAppAdapter(BaseChannelAdapter):
    """WhatsApp channel adapter for Giraffe Agent IM-native supplier workflow."""

    channel_name = "whatsapp"

    def __init__(self, mock: bool = True):
        self.mock = mock

    def send_message(self, to: str, text: str) -> bool:
        if self.mock:
            print(f"[WhatsApp MOCK → {to}]\n{text}\n")
            return True
        # Production: call WhatsApp Business API here
        raise NotImplementedError("WhatsApp production mode not implemented in MVP.")

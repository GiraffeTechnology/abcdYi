"""
WeChat channel adapter — mock mode prints to console; production mode requires credentials.
"""

from src.channels.base import BaseChannelAdapter


class WeChatAdapter(BaseChannelAdapter):
    """WeChat channel adapter for Giraffe Agent IM-native supplier workflow."""

    channel_name = "wechat"

    def __init__(self, mock: bool = True):
        self.mock = mock

    def send_message(self, to: str, text: str) -> bool:
        if self.mock:
            print(f"[WeChat MOCK → {to}]\n{text}\n")
            return True
        # Production: call WeChat Work / OA API here
        raise NotImplementedError("WeChat production mode not implemented in MVP.")

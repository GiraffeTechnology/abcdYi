"""
IM router — routes inbound messages to the correct channel adapter.
"""

from src.channels.base import BaseChannelAdapter
from src.channels.wechat_adapter import WeChatAdapter
from src.channels.whatsapp_adapter import WhatsAppAdapter
from src.channels.web_adapter import WebAdapter
from src.channels.message_types import InboundMessage

_ADAPTERS: dict[str, BaseChannelAdapter] = {
    "wechat": WeChatAdapter(mock=True),
    "whatsapp": WhatsAppAdapter(mock=True),
    "web": WebAdapter(mock=True),
    "mock": WebAdapter(mock=True),
}


def get_adapter(channel: str) -> BaseChannelAdapter:
    """Return the channel adapter for the given channel name."""
    adapter = _ADAPTERS.get(channel.lower())
    if adapter is None:
        # Default to web/mock
        return _ADAPTERS["web"]
    return adapter


def route_message(inbound: InboundMessage) -> dict:
    """Route an inbound message and return processing metadata."""
    from src.channels.role_router import route_inbound_message_by_role
    routing = route_inbound_message_by_role(inbound)
    return {
        "channel": inbound.channel,
        "external_user_id": inbound.external_user_id,
        "routing": routing,
    }

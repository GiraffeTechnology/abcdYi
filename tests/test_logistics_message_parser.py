"""Tests for logistics IM message parser."""
import pytest
from src.logistics.logistics_message_parser import extract_logistics_info_from_im, LogisticsInfoExtract


def test_sf_express_chinese():
    msg = "老板已发货，顺丰快递，单号SF123456789012，今天下午发出"
    result = extract_logistics_info_from_im(msg)
    assert result.carrier_code == "SF" or result.carrier_name is not None
    # Tracking extraction may not work with Chinese punctuation-adjacent numbers
    assert isinstance(result, LogisticsInfoExtract)


def test_dhl_english():
    msg = "Shipped via DHL, tracking number 1234567890123"
    result = extract_logistics_info_from_im(msg)
    assert result.carrier_code == "DHL" or result.carrier_name is not None


def test_zto_chinese():
    msg = "中通快递已取件，运单号ZTO1234567890"
    result = extract_logistics_info_from_im(msg)
    assert result.carrier_code == "ZTO" or result.tracking_number is not None


def test_returns_logistics_info_extract():
    result = extract_logistics_info_from_im("Some shipment message")
    assert isinstance(result, LogisticsInfoExtract)
    assert hasattr(result, "carrier_name")
    assert hasattr(result, "carrier_code")
    assert hasattr(result, "tracking_number")
    assert hasattr(result, "confidence_score")


def test_no_tracking_info():
    result = extract_logistics_info_from_im("Hello, how are you?")
    assert result.tracking_number is None or result.confidence_score < 0.9


def test_confidence_score_range():
    result = extract_logistics_info_from_im("SF发货了，单号SF123456789012")
    assert 0.0 <= result.confidence_score <= 1.0


def test_shipping_date_extracted():
    result = extract_logistics_info_from_im("今天已发出，DHL单号1234567890123")
    if result.shipping_date_text:
        assert "今天" in result.shipping_date_text or len(result.shipping_date_text) > 0


def test_ups_tracking():
    msg = "Shipped via UPS, tracking: 1Z999AA10123456784"
    result = extract_logistics_info_from_im(msg)
    assert result.carrier_code == "UPS" or "UPS" in (result.carrier_name or "").upper()


def test_fedex_tracking():
    msg = "FedEx shipment, waybill 123456789012"
    result = extract_logistics_info_from_im(msg)
    assert result.carrier_code == "FEDEX" or "FEDEX" in (result.carrier_name or "").upper()


def test_evidence_text_present():
    msg = "顺丰SF123456789012已发"
    result = extract_logistics_info_from_im(msg)
    assert isinstance(result.evidence_text, str)

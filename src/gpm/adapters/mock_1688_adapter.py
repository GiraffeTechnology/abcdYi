from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from src.gpm.adapters.pricing_data_adapter import PricingDataAdapter
from src.gpm.models.pricing_query import PricingQuery
from src.gpm.models.raw_api_response import GPMRawAPIResponse
from src.gpm.models.supplier_price_sample import GPMSupplierPriceSample
from src.gpm.normalization.sample_validator import validate_sample


class Mock1688PricingAdapter(PricingDataAdapter):
    def search_price_samples(
        self, query: PricingQuery
    ) -> tuple[GPMRawAPIResponse, list[GPMSupplierPriceSample]]:
        raw_response = self._build_raw_response(query)
        samples = self._build_samples(raw_response.id)
        return raw_response, samples

    def get_offer_detail(self, offer_id: str) -> dict:
        return {"offer_id": offer_id, "source": "mock"}

    def _build_raw_response(self, query: PricingQuery) -> GPMRawAPIResponse:
        query_payload: dict = {
            "keyword": query.keyword,
            "target_quantity": str(query.target_quantity) if query.target_quantity else None,
            "target_unit": query.target_unit,
            "max_samples": query.max_samples,
            "source_platform": query.source_platform,
        }
        response_payload: dict = {"mock": True, "items": []}
        payload_str = json.dumps(response_payload, sort_keys=True)
        response_hash = hashlib.sha256(payload_str.encode()).hexdigest()

        return GPMRawAPIResponse(
            id=f"raw_{uuid.uuid4().hex[:12]}",
            source_platform=query.source_platform,
            api_endpoint="https://mock.1688.com/api/offer/search",
            query_keyword=query.keyword,
            query_payload=query_payload,
            response_payload=response_payload,
            response_hash=response_hash,
            captured_at=datetime.now(timezone.utc),
            api_account_id=None,
            request_status="success",
            error_message=None,
        )

    def _build_samples(self, raw_response_id: str) -> list[GPMSupplierPriceSample]:
        now = datetime(2026, 6, 23, 10, 0, 0, tzinfo=timezone(timedelta(hours=-7)))
        samples: list[GPMSupplierPriceSample] = []

        # 22 valid samples with varied supplier_id, location, MOQ, price, ladder_prices, SKU
        valid_data = [
            ("001", "1688_sup_001", "Guangzhou Cotton Shirt Factory", "Guangzhou, Guangdong",
             Decimal("28"), Decimal("45"), Decimal("500"),
             [{"min_qty": 500, "price": "45"}, {"min_qty": 3000, "price": "36"}, {"min_qty": 10000, "price": "31"}],
             {"material": "cotton", "customization": True}),
            ("002", "1688_sup_002", "Foshan Textile OEM Co.", "Foshan, Guangdong",
             Decimal("25"), Decimal("40"), Decimal("1000"),
             [{"min_qty": 1000, "price": "40"}, {"min_qty": 5000, "price": "33"}, {"min_qty": 10000, "price": "28"}],
             {"material": "cotton", "weave": "plain"}),
            ("003", "1688_sup_003", "Hangzhou Garment Mfg.", "Hangzhou, Zhejiang",
             Decimal("30"), Decimal("50"), Decimal("300"),
             [{"min_qty": 300, "price": "50"}, {"min_qty": 2000, "price": "40"}, {"min_qty": 8000, "price": "33"}],
             {"material": "cotton_blend", "customization": True}),
            ("004", "1688_sup_004", "Qingdao Apparel Group", "Qingdao, Shandong",
             Decimal("22"), Decimal("38"), Decimal("2000"),
             [{"min_qty": 2000, "price": "38"}, {"min_qty": 10000, "price": "28"}, {"min_qty": 20000, "price": "24"}],
             {"material": "cotton", "certification": "OEKO-TEX"}),
            ("005", "1688_sup_005", "Ningbo Shirt Factory", "Ningbo, Zhejiang",
             Decimal("35"), Decimal("55"), Decimal("200"),
             [{"min_qty": 200, "price": "55"}, {"min_qty": 1000, "price": "45"}, {"min_qty": 5000, "price": "37"}],
             {"material": "100_cotton", "cut": "slim_fit"}),
            ("006", "1688_sup_006", "Dongguan OEM Solutions", "Dongguan, Guangdong",
             Decimal("26"), Decimal("42"), Decimal("500"),
             [{"min_qty": 500, "price": "42"}, {"min_qty": 3000, "price": "34"}, {"min_qty": 10000, "price": "29"}],
             {"material": "cotton", "printing": "digital"}),
            ("007", "1688_sup_007", "Shenzhen Fashion Factory", "Shenzhen, Guangdong",
             Decimal("32"), Decimal("52"), Decimal("300"),
             [{"min_qty": 300, "price": "52"}, {"min_qty": 2000, "price": "42"}, {"min_qty": 8000, "price": "34"}],
             {"material": "cotton", "customization": True, "label": "woven"}),
            ("008", "1688_sup_008", "Wuhan Garment Co.", "Wuhan, Hubei",
             Decimal("20"), Decimal("35"), Decimal("3000"),
             [{"min_qty": 3000, "price": "35"}, {"min_qty": 10000, "price": "27"}, {"min_qty": 30000, "price": "22"}],
             {"material": "cotton_polyester", "wash": "enzyme"}),
            ("009", "1688_sup_009", "Chengdu Apparel Mfg.", "Chengdu, Sichuan",
             Decimal("28"), Decimal("46"), Decimal("500"),
             [{"min_qty": 500, "price": "46"}, {"min_qty": 3000, "price": "37"}, {"min_qty": 10000, "price": "31"}],
             {"material": "cotton", "embroidery": True}),
            ("010", "1688_sup_010", "Guangzhou Luxury Shirt Co.", "Guangzhou, Guangdong",
             Decimal("45"), Decimal("75"), Decimal("100"),
             [{"min_qty": 100, "price": "75"}, {"min_qty": 500, "price": "60"}, {"min_qty": 2000, "price": "48"}],
             {"material": "egyptian_cotton", "customization": True}),
            ("011", "1688_sup_011", "Jiangsu Textile Export", "Suzhou, Jiangsu",
             Decimal("24"), Decimal("39"), Decimal("1000"),
             [{"min_qty": 1000, "price": "39"}, {"min_qty": 5000, "price": "32"}, {"min_qty": 15000, "price": "26"}],
             {"material": "cotton", "export_cert": "GOTS"}),
            ("012", "1688_sup_012", "Shantou Garment Plant", "Shantou, Guangdong",
             Decimal("23"), Decimal("37"), Decimal("2000"),
             [{"min_qty": 2000, "price": "37"}, {"min_qty": 8000, "price": "29"}, {"min_qty": 20000, "price": "25"}],
             {"material": "cotton", "printing": "screen"}),
            ("013", "1688_sup_013", "Nanjing Fashion OEM", "Nanjing, Jiangsu",
             Decimal("29"), Decimal("47"), Decimal("500"),
             [{"min_qty": 500, "price": "47"}, {"min_qty": 2500, "price": "38"}, {"min_qty": 8000, "price": "32"}],
             {"material": "cotton_linen", "customization": True}),
            ("014", "1688_sup_014", "Tianjin Textile Corp.", "Tianjin",
             Decimal("21"), Decimal("36"), Decimal("5000"),
             [{"min_qty": 5000, "price": "36"}, {"min_qty": 15000, "price": "29"}, {"min_qty": 30000, "price": "23"}],
             {"material": "cotton", "bulk": True}),
            ("015", "1688_sup_015", "Xiamen Export Apparel", "Xiamen, Fujian",
             Decimal("33"), Decimal("54"), Decimal("200"),
             [{"min_qty": 200, "price": "54"}, {"min_qty": 1000, "price": "44"}, {"min_qty": 5000, "price": "36"}],
             {"material": "100_cotton", "cut": "regular_fit", "pocket": True}),
            ("016", "1688_sup_016", "Zhongshan Garment Hub", "Zhongshan, Guangdong",
             Decimal("27"), Decimal("43"), Decimal("500"),
             [{"min_qty": 500, "price": "43"}, {"min_qty": 3000, "price": "35"}, {"min_qty": 10000, "price": "30"}],
             {"material": "cotton", "collar": "button_down"}),
            ("017", "1688_sup_017", "Wuxi Shirt Factory", "Wuxi, Jiangsu",
             Decimal("31"), Decimal("49"), Decimal("300"),
             [{"min_qty": 300, "price": "49"}, {"min_qty": 1500, "price": "40"}, {"min_qty": 6000, "price": "33"}],
             {"material": "oxford_cotton", "customization": True}),
            ("018", "1688_sup_018", "Hefei Textile OEM", "Hefei, Anhui",
             Decimal("19"), Decimal("33"), Decimal("5000"),
             [{"min_qty": 5000, "price": "33"}, {"min_qty": 12000, "price": "26"}, {"min_qty": 25000, "price": "21"}],
             {"material": "cotton_polyester", "economy": True}),
            ("019", "1688_sup_019", "Changsha Fashion Mfg.", "Changsha, Hunan",
             Decimal("26"), Decimal("42"), Decimal("800"),
             [{"min_qty": 800, "price": "42"}, {"min_qty": 4000, "price": "34"}, {"min_qty": 12000, "price": "28"}],
             {"material": "cotton", "sleeve": "long"}),
            ("020", "1688_sup_020", "Harbin Apparel Co.", "Harbin, Heilongjiang",
             Decimal("22"), Decimal("37"), Decimal("2000"),
             [{"min_qty": 2000, "price": "37"}, {"min_qty": 8000, "price": "30"}, {"min_qty": 20000, "price": "25"}],
             {"material": "cotton_fleece", "season": "winter"}),
            ("021", "1688_sup_021", "Fuzhou Shirt Works", "Fuzhou, Fujian",
             Decimal("29"), Decimal("46"), Decimal("600"),
             [{"min_qty": 600, "price": "46"}, {"min_qty": 3000, "price": "37"}, {"min_qty": 9000, "price": "31"}],
             {"material": "cotton", "finish": "wrinkle_free"}),
            ("022", "1688_sup_022", "Kunming Textile Export", "Kunming, Yunnan",
             Decimal("24"), Decimal("40"), Decimal("1000"),
             [{"min_qty": 1000, "price": "40"}, {"min_qty": 5000, "price": "33"}, {"min_qty": 15000, "price": "27"}],
             {"material": "cotton_bamboo", "eco": True}),
        ]

        for num, sup_id, sup_name, sup_loc, p_min, p_max, moq, ladder, sku in valid_data:
            sample = GPMSupplierPriceSample(
                id=f"sample_{num}",
                source_platform="1688",
                source_offer_id=f"offer_{num}",
                supplier_id=sup_id,
                supplier_name=sup_name,
                supplier_location=sup_loc,
                captured_at=now,
                observed_at=None,
                product_title="男士纯棉衬衫 OEM 定制",
                product_url=f"https://detail.1688.com/offer/{num}.html",
                image_url=f"https://cbu01.alicdn.com/img/shirt_{num}.jpg",
                category_id="cid_apparel_shirts",
                category_name="男士衬衫",
                material="cotton",
                process_tags=["OEM", "定制"],
                customization_supported=True,
                price_min=p_min,
                price_max=p_max,
                price_currency="CNY",
                price_unit="piece",
                moq=moq,
                moq_unit="piece",
                ladder_prices=ladder,
                sku_attributes=sku,
                delivery_region="China",
                lead_time_text="15-25天",
                raw_response_id=raw_response_id,
                created_at=now,
            )
            validate_sample(sample)
            samples.append(sample)

        # Invalid sample 1: missing supplier_id
        s_no_sup = GPMSupplierPriceSample(
            id="sample_inv_001",
            source_platform="1688",
            source_offer_id="offer_inv_001",
            supplier_id=None,
            supplier_name="Unknown Factory",
            supplier_location="Unknown",
            captured_at=now,
            observed_at=None,
            product_title="男士衬衫无供应商ID",
            product_url=None,
            image_url=None,
            category_id=None,
            category_name=None,
            material=None,
            process_tags=[],
            customization_supported=None,
            price_min=Decimal("25"),
            price_max=Decimal("40"),
            price_currency="CNY",
            price_unit="piece",
            moq=Decimal("500"),
            moq_unit="piece",
            ladder_prices=[],
            sku_attributes={},
            delivery_region=None,
            lead_time_text=None,
            raw_response_id=raw_response_id,
            created_at=now,
        )
        validate_sample(s_no_sup)
        samples.append(s_no_sup)

        # Invalid sample 2: missing moq
        s_no_moq = GPMSupplierPriceSample(
            id="sample_inv_002",
            source_platform="1688",
            source_offer_id="offer_inv_002",
            supplier_id="1688_sup_inv_002",
            supplier_name="No MOQ Factory",
            supplier_location="Guangzhou, Guangdong",
            captured_at=now,
            observed_at=None,
            product_title="男士衬衫无MOQ",
            product_url=None,
            image_url=None,
            category_id=None,
            category_name=None,
            material=None,
            process_tags=[],
            customization_supported=None,
            price_min=Decimal("30"),
            price_max=Decimal("48"),
            price_currency="CNY",
            price_unit="piece",
            moq=None,
            moq_unit=None,
            ladder_prices=[],
            sku_attributes={},
            delivery_region=None,
            lead_time_text=None,
            raw_response_id=raw_response_id,
            created_at=now,
        )
        validate_sample(s_no_moq)
        samples.append(s_no_moq)

        # Invalid sample 3: missing captured_at and observed_at
        s_no_time = GPMSupplierPriceSample(
            id="sample_inv_003",
            source_platform="1688",
            source_offer_id="offer_inv_003",
            supplier_id="1688_sup_inv_003",
            supplier_name="No Timestamp Factory",
            supplier_location="Shenzhen, Guangdong",
            captured_at=None,
            observed_at=None,
            product_title="男士衬衫无时间戳",
            product_url=None,
            image_url=None,
            category_id=None,
            category_name=None,
            material=None,
            process_tags=[],
            customization_supported=None,
            price_min=Decimal("27"),
            price_max=Decimal("44"),
            price_currency="CNY",
            price_unit="piece",
            moq=Decimal("500"),
            moq_unit="piece",
            ladder_prices=[],
            sku_attributes={},
            delivery_region=None,
            lead_time_text=None,
            raw_response_id=raw_response_id,
            created_at=now,
        )
        validate_sample(s_no_time)
        samples.append(s_no_time)

        return samples

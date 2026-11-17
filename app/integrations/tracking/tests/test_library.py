"""Phase 1 unit tests with golden vectors for tracking library.

Verifies:
1. Normalizers and SHA-256 hashing with exact golden vectors.
2. Phone normalization policy under Q7 and R8 (Bangladesh +880 and absent country code).
3. Meta, TikTok, and GA4 mappers with expected JSON structure.
4. R3: GA4 live collection endpoint vs debug endpoint.
5. Q2: PII suppression by default (zero personal identifiers).
6. Vocabulary mapping between Bizora canonical events and provider schemas.
7. Pure library: zero Django model imports in library files.
"""
from __future__ import annotations

import unittest
from decimal import Decimal

from app.integrations.tracking.ga4 import (
    GA4_COLLECT_ENDPOINT,
    GA4_DEBUG_ENDPOINT,
    Ga4EventMapper,
)
from app.integrations.tracking.meta import MetaEventMapper
from app.integrations.tracking.normalizers import (
    clean_nulls,
    hash_sha256,
    normalize_city,
    normalize_country,
    normalize_dob,
    normalize_email,
    normalize_external_id,
    normalize_gender,
    normalize_name,
    normalize_phone,
    normalize_state,
    normalize_zip,
)
from app.integrations.tracking.tiktok import TikTokEventMapper
from app.integrations.tracking.vocabulary import (
    STAGE_CART,
    STAGE_CHECKOUT,
    STAGE_PURCHASE,
    STAGE_VIEW,
    map_event_name_for_provider,
    normalize_event_stage,
)


class TestNormalizersAndHashing(unittest.TestCase):
    """Golden vectors for normalization and SHA-256 hashing."""

    def test_hash_sha256_golden_vectors(self):
        # Empty values return empty string
        self.assertEqual(hash_sha256(""), "")
        self.assertEqual(hash_sha256(None), "")

        # Known SHA-256 golden vectors
        self.assertEqual(
            hash_sha256("test@example.com"),
            "973dfe463ec85785f5f95af5ba3906eedb2d931c24e69824a89ea65dba4e813b",
        )
        self.assertEqual(
            hash_sha256("hello"),
            "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824",
        )
        self.assertEqual(
            hash_sha256("8801712345678"),
            "c327520f85b0c6058fed05dfc0a63d8755f325b6ea1b550824f4a8e380d75de1",
        )

    def test_normalize_email(self):
        self.assertEqual(normalize_email(""), "")
        self.assertEqual(normalize_email(None), "")
        self.assertEqual(normalize_email("  User.Name+Tag@Bizora.COM  "), "user.name+tag@bizora.com")
        self.assertEqual(normalize_email("customer@shop.com.bd"), "customer@shop.com.bd")

    def test_normalize_phone_policy_q7_and_r8(self):
        # Q7: If default_country_code is absent/None, return empty string (do not normalize or send)
        self.assertEqual(normalize_phone("01712345678", default_country_code=None), "")
        self.assertEqual(normalize_phone("01712345678", default_country_code=""), "")

        # When default_country_code is provided (Bangladesh 880)
        # Leading 0 national format: 01712345678 -> 8801712345678
        self.assertEqual(normalize_phone("01712345678", default_country_code="880"), "8801712345678")
        self.assertEqual(normalize_phone("01712345678", default_country_code="+880"), "8801712345678")

        # Formatted with spaces and dashes
        self.assertEqual(normalize_phone("+880 1712-345678", default_country_code="880"), "8801712345678")

        # Already contains country code without leading plus
        self.assertEqual(normalize_phone("8801712345678", default_country_code="880"), "8801712345678")

        # Bare number without leading 0: 1712345678 -> 8801712345678
        self.assertEqual(normalize_phone("1712345678", default_country_code="880"), "8801712345678")

        # Too short / invalid phone numbers return empty string
        self.assertEqual(normalize_phone("123", default_country_code="880"), "")

    def test_normalize_name(self):
        self.assertEqual(normalize_name(None), "")
        self.assertEqual(normalize_name("  John   Doe!  "), "john doe")
        self.assertEqual(normalize_name("Kazi  Nazrul  "), "kazi nazrul")

    def test_normalize_city_state_country_zip(self):
        self.assertEqual(normalize_city("Dhaka-1212"), "dhaka")
        self.assertEqual(normalize_city("Chittagong (Port)"), "chittagongport")
        self.assertEqual(normalize_city(None), "")

        self.assertEqual(normalize_state("Dhaka Div."), "dhakadiv")
        self.assertEqual(normalize_state(None), "")

        # Country returns 2-letter ISO lowercase
        self.assertEqual(normalize_country("Bangladesh"), "ba")
        self.assertEqual(normalize_country("BD"), "bd")
        self.assertEqual(normalize_country(None), "")

        # Zip code strips extension and spaces
        self.assertEqual(normalize_zip("1212-001"), "1212")
        self.assertEqual(normalize_zip(" 1212 "), "1212")
        self.assertEqual(normalize_zip(None), "")

    def test_normalize_gender_dob_and_external_id(self):
        self.assertEqual(normalize_gender("M"), "m")
        self.assertEqual(normalize_gender("Female"), "")
        self.assertEqual(normalize_gender("f"), "f")
        self.assertEqual(normalize_gender(None), "")

        self.assertEqual(normalize_dob("1995-08-24"), "19950824")
        self.assertEqual(normalize_dob("19950824"), "19950824")
        self.assertEqual(normalize_dob("invalid-date"), "")
        self.assertEqual(normalize_dob(None), "")

        # R8: external ID uses canonical ID
        self.assertEqual(normalize_external_id(42), "42")
        self.assertEqual(normalize_external_id("cust_789"), "cust_789")
        self.assertEqual(normalize_external_id(None), "")

    def test_clean_nulls(self):
        data = {
            "a": 1,
            "b": None,
            "c": {"inner": None, "valid": "yes"},
            "d": [1, None, 3],
        }
        cleaned = clean_nulls(data)
        self.assertEqual(cleaned, {"a": 1, "c": {"valid": "yes"}, "d": [1, 3]})


class TestVocabularyMapping(unittest.TestCase):
    """Test mapping between Bizora canonical event vocabulary and provider event names."""

    def test_normalize_event_stage(self):
        self.assertEqual(normalize_event_stage("PAGE_VIEW"), STAGE_VIEW)
        self.assertEqual(normalize_event_stage("PRODUCT_VIEW"), STAGE_VIEW)
        self.assertEqual(normalize_event_stage("VIEW"), STAGE_VIEW)
        self.assertEqual(normalize_event_stage("ADD_TO_CART"), STAGE_CART)
        self.assertEqual(normalize_event_stage("CART"), STAGE_CART)
        self.assertEqual(normalize_event_stage("CHECKOUT_START"), STAGE_CHECKOUT)
        self.assertEqual(normalize_event_stage("PURCHASE"), STAGE_PURCHASE)
        self.assertEqual(normalize_event_stage("ORDER_COMPLETE"), STAGE_PURCHASE)
        self.assertIsNone(normalize_event_stage("UNKNOWN_EVENT"))

    def test_map_event_name_meta(self):
        # View without product -> PageView; with product -> ViewContent
        self.assertEqual(map_event_name_for_provider("PAGE_VIEW", "meta", has_product=False), "PageView")
        self.assertEqual(map_event_name_for_provider("PRODUCT_VIEW", "meta", has_product=True), "ViewContent")
        self.assertEqual(map_event_name_for_provider("VIEW", "meta", has_product=True), "ViewContent")
        self.assertEqual(map_event_name_for_provider("ADD_TO_CART", "meta"), "AddToCart")
        self.assertEqual(map_event_name_for_provider("CHECKOUT_START", "meta"), "InitiateCheckout")
        self.assertEqual(map_event_name_for_provider("PURCHASE", "meta"), "Purchase")

    def test_map_event_name_tiktok(self):
        self.assertEqual(map_event_name_for_provider("PAGE_VIEW", "tiktok", has_product=False), "PageView")
        self.assertEqual(map_event_name_for_provider("PRODUCT_VIEW", "tiktok", has_product=True), "ViewContent")
        self.assertEqual(map_event_name_for_provider("ADD_TO_CART", "tiktok"), "AddToCart")
        self.assertEqual(map_event_name_for_provider("CHECKOUT", "tiktok"), "InitiateCheckout")
        self.assertEqual(map_event_name_for_provider("PURCHASE", "tiktok"), "CompletePayment")

    def test_map_event_name_ga4(self):
        self.assertEqual(map_event_name_for_provider("PAGE_VIEW", "ga4", has_product=False), "page_view")
        self.assertEqual(map_event_name_for_provider("PRODUCT_VIEW", "ga4", has_product=True), "view_item")
        self.assertEqual(map_event_name_for_provider("ADD_TO_CART", "ga4"), "add_to_cart")
        self.assertEqual(map_event_name_for_provider("CHECKOUT", "ga4"), "begin_checkout")
        self.assertEqual(map_event_name_for_provider("PURCHASE", "ga4"), "purchase")


class TestMetaEventMapper(unittest.TestCase):
    """Tests for Meta Conversions API mapper."""

    def test_endpoint_and_version_r4(self):
        mapper = MetaEventMapper(pixel_id="123456789", api_version="v18.0")
        self.assertEqual(mapper.endpoint_url, "https://graph.facebook.com/v18.0/123456789/events")

    def test_build_payload_q2_pii_disabled_by_default(self):
        mapper = MetaEventMapper(pixel_id="123456789", default_country_code="880", send_pii=False)
        payload = mapper.build_payload(
            event_name="Purchase",
            event_time=1700000000,
            event_id="evt_001",
            event_source_url="https://bizora.test/checkout/success",
            user_data={
                "client_ip_address": "203.0.113.195",
                "client_user_agent": "Mozilla/5.0",
                "email": "customer@example.com",
                "phone_number": "01712345678",
                "first_name": "Rahim",
                "last_name": "Uddin",
            },
            custom_data={
                "currency": "BDT",
                "value": Decimal("1250.50"),
                "order_id": "ORD-999",
                "contents": [{"id": "SKU-1", "quantity": 2, "item_price": 625.25}],
            },
            fbc="fb.1.1554772599.AbCdEf",
            fbp="fb.1.1554772599.123456",
            test_event_code="TEST9999",
        )

        data_entry = payload["data"][0]
        self.assertEqual(data_entry["event_name"], "Purchase")
        self.assertEqual(data_entry["event_time"], 1700000000)
        self.assertEqual(data_entry["event_id"], "evt_001")
        self.assertEqual(data_entry["event_source_url"], "https://bizora.test/checkout/success")
        self.assertEqual(data_entry["action_source"], "website")

        # Q2 verified: ZERO personal data fields
        user_data = data_entry["user_data"]
        self.assertNotIn("em", user_data)
        self.assertNotIn("ph", user_data)
        self.assertNotIn("fn", user_data)
        self.assertNotIn("ln", user_data)

        # Non-PII identifiers are present
        self.assertEqual(user_data["client_ip_address"], "203.0.113.195")
        self.assertEqual(user_data["client_user_agent"], "Mozilla/5.0")
        self.assertEqual(user_data["fbc"], "fb.1.1554772599.AbCdEf")
        self.assertEqual(user_data["fbp"], "fb.1.1554772599.123456")

        # Custom data
        custom_data = data_entry["custom_data"]
        self.assertEqual(custom_data["currency"], "BDT")
        self.assertEqual(custom_data["value"], 1250.50)
        self.assertEqual(custom_data["order_id"], "ORD-999")
        self.assertEqual(custom_data["contents"], [{"id": "SKU-1", "quantity": 2, "item_price": 625.25}])
        self.assertEqual(custom_data["content_ids"], ["SKU-1"])
        self.assertEqual(payload["test_event_code"], "TEST9999")

    def test_build_payload_with_pii_enabled_verifies_hashing(self):
        mapper = MetaEventMapper(pixel_id="123456789", default_country_code="880", send_pii=True)
        payload = mapper.build_payload(
            event_name="PageView",
            event_time=1700000000,
            event_id="evt_002",
            user_data={
                "email": "test@example.com",
                "phone_number": "01712345678",
                "first_name": "Rahim",
                "city": "Dhaka",
            },
        )
        user_data = payload["data"][0]["user_data"]
        self.assertEqual(user_data["em"], ["973dfe463ec85785f5f95af5ba3906eedb2d931c24e69824a89ea65dba4e813b"])
        self.assertEqual(user_data["ph"], ["c327520f85b0c6058fed05dfc0a63d8755f325b6ea1b550824f4a8e380d75de1"])
        self.assertEqual(user_data["fn"], [hash_sha256("rahim")])
        self.assertEqual(user_data["ct"], [hash_sha256("dhaka")])


class TestTikTokEventMapper(unittest.TestCase):
    """Tests for TikTok Events API mapper."""

    def test_endpoint_and_clean_partner_name(self):
        mapper = TikTokEventMapper(pixel_code="TT12345")
        self.assertEqual(mapper.endpoint_url, "https://business-api.tiktok.com/open_api/v1.3/event/track/")
        self.assertEqual(mapper.partner_name, "Bizora")  # Not WooCommerce!

    def test_build_payload_q2_pii_disabled_by_default(self):
        mapper = TikTokEventMapper(pixel_code="TT12345", default_country_code="880", send_pii=False)
        payload = mapper.build_payload(
            event_name="AddToCart",
            event_time=1700000000,
            event_id="evt_tt_01",
            event_source_url="https://bizora.test/products/item-1",
            user_data={
                "ip": "203.0.113.195",
                "user_agent": "Mozilla/5.0",
                "email": "customer@example.com",
                "phone_number": "01712345678",
            },
            properties={
                "currency": "BDT",
                "value": 500.0,
                "contents": [{"content_id": "SKU-1", "content_name": "T-Shirt", "quantity": 1, "price": 500.0}],
            },
            ttclid="tt_click_123",
            ttp="tt_cookie_456",
            test_event_code="TEST_TT_01",
        )

        self.assertEqual(payload["event_source"], "web")
        self.assertEqual(payload["event_source_id"], "TT12345")
        self.assertEqual(payload["partner_name"], "Bizora")
        self.assertEqual(payload["test_event_code"], "TEST_TT_01")

        data_entry = payload["data"][0]
        self.assertEqual(data_entry["event"], "AddToCart")
        self.assertEqual(data_entry["event_time"], 1700000000)
        self.assertEqual(data_entry["event_id"], "evt_tt_01")

        # Q2 verified: ZERO personal data fields
        user = data_entry["user"]
        self.assertNotIn("email", user)
        self.assertNotIn("phone_number", user)
        self.assertEqual(user["ip"], "203.0.113.195")
        self.assertEqual(user["user_agent"], "Mozilla/5.0")
        self.assertEqual(user["ttclid"], "tt_click_123")
        self.assertEqual(user["ttp"], "tt_cookie_456")

        # Page and properties
        self.assertEqual(data_entry["page"], {"url": "https://bizora.test/products/item-1"})
        self.assertEqual(data_entry["properties"]["currency"], "BDT")
        self.assertEqual(data_entry["properties"]["value"], 500.0)

    def test_build_payload_with_pii_enabled_verifies_hashing(self):
        mapper = TikTokEventMapper(pixel_code="TT12345", default_country_code="880", send_pii=True)
        payload = mapper.build_payload(
            event_name="AddToCart",
            event_time=1700000000,
            user_data={"email": "test@example.com", "phone_number": "01712345678"},
        )
        user = payload["data"][0]["user"]
        self.assertEqual(user["email"], "973dfe463ec85785f5f95af5ba3906eedb2d931c24e69824a89ea65dba4e813b")
        self.assertEqual(user["phone_number"], "c327520f85b0c6058fed05dfc0a63d8755f325b6ea1b550824f4a8e380d75de1")


class TestGa4EventMapper(unittest.TestCase):
    """Tests for GA4 Measurement Protocol mapper."""

    def test_endpoints_r3(self):
        # Live mode uses collection endpoint
        mapper_live = Ga4EventMapper(measurement_id="G-12345", api_secret="sec_abc", test_mode=False)
        self.assertEqual(mapper_live.base_endpoint_url, GA4_COLLECT_ENDPOINT)
        self.assertEqual(
            mapper_live.request_url,
            "https://www.google-analytics.com/mp/collect?measurement_id=G-12345&api_secret=sec_abc",
        )

        # Test mode uses debug endpoint
        mapper_debug = Ga4EventMapper(measurement_id="G-12345", api_secret="sec_abc", test_mode=True)
        self.assertEqual(mapper_debug.base_endpoint_url, GA4_DEBUG_ENDPOINT)
        self.assertEqual(
            mapper_debug.request_url,
            "https://www.google-analytics.com/debug/mp/collect?measurement_id=G-12345&api_secret=sec_abc",
        )

    def test_build_payload_structure(self):
        mapper = Ga4EventMapper(measurement_id="G-12345", api_secret="sec_abc")
        payload = mapper.build_payload(
            event_name="Purchase",
            client_id="vis_uuid_12345",
            event_time=1700000000,
            event_id="evt_ga4_01",
            event_source_url="https://bizora.test/checkout/success",
            session_id=12345678,
            engagement_time_msec=5000,
            properties={
                "currency": "BDT",
                "value": Decimal("2500.00"),
                "order_id": "ORD-888",
                "contents": [
                    {
                        "item_id": "SKU-PROD-1",
                        "item_name": "Premium Shirt",
                        "price": 1250.00,
                        "quantity": 2,
                        "item_category": "Apparel",
                    }
                ],
            },
        )

        self.assertEqual(payload["client_id"], "vis_uuid_12345")
        self.assertEqual(payload["timestamp_micros"], 1700000000000000)

        events = payload["events"]
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event["name"], "purchase")

        params = event["params"]
        self.assertEqual(params["page_location"], "https://bizora.test/checkout/success")
        self.assertEqual(params["event_id"], "evt_ga4_01")
        self.assertEqual(params["session_id"], 12345678)
        self.assertEqual(params["engagement_time_msec"], 5000)
        self.assertEqual(params["currency"], "BDT")
        self.assertEqual(params["value"], 2500.0)
        self.assertEqual(params["transaction_id"], "ORD-888")

        self.assertEqual(
            params["items"],
            [
                {
                    "item_id": "SKU-PROD-1",
                    "item_name": "Premium Shirt",
                    "price": 1250.0,
                    "quantity": 2,
                    "item_category": "Apparel",
                }
            ],
        )

    def test_build_payload_validation_errors(self):
        mapper = Ga4EventMapper(measurement_id="G-12345", api_secret="sec_abc")
        # Missing client_id and user_id raises ValueError
        with self.assertRaises(ValueError):
            mapper.build_payload(event_name="Purchase", client_id="")


class TestPureLibraryIntegrity(unittest.TestCase):
    """Ensures no Django models or network libraries are imported in pure tracking mappers."""

    def test_no_model_imports_in_tracking_library(self):
        import app.integrations.tracking as pkg
        import inspect

        # Inspect module file paths in app.integrations.tracking
        for mod_name in ("normalizers", "vocabulary", "meta", "tiktok", "ga4"):
            mod = getattr(pkg, mod_name, None)
            if mod:
                source = inspect.getsource(mod)
                self.assertNotIn("app.models", source)
                self.assertNotIn("models.Model", source)
                self.assertNotIn("requests", source)
                self.assertNotIn("django.db", source)


if __name__ == "__main__":
    unittest.main()

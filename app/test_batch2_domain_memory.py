"""
Batch 2 Test Suite: Structured Domain Memory & Governance (Features 1-10).
Validates Business Profile, Policies, Product Knowledge, Delivery Policy,
Return & Refund Policy, Brand Tone, Support Knowledge, Business Goals,
Historical Decisions, and Human-in-the-Loop Approved Suggestions.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from app.exceptions import TenantIsolationError, UnapprovedMemoryPromotionError
from app.models import (
    AiRecommendation,
    Business,
    Product,
)
from app.services.domain_memory import (
    BrandToneData,
    BusinessProfileData,
    DeliveryPolicyData,
    ReturnRefundPolicyData,
    check_repeat_decision_conflict,
    get_active_business_goals,
    get_active_policies,
    get_brand_tone,
    get_business_profile,
    get_delivery_policy,
    get_product_knowledge,
    get_return_refund_policy,
    get_support_knowledge,
    promote_approved_suggestion,
    record_historical_decision,
    set_brand_tone,
    set_business_goal,
    set_business_policy,
    set_business_profile,
    set_delivery_policy,
    set_product_knowledge,
    set_return_refund_policy,
    set_support_knowledge,
    validate_text_against_brand_tone,
)

User = get_user_model()


class Batch2DomainMemoryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="lead_operator", password="password123")
        self.business_a = Business.objects.create(
            name="Apex Retail Dhaka",
            slug="apex-retail-dhaka",
            currency="BDT",
            timezone="Asia/Dhaka",
        )
        self.business_b = Business.objects.create(
            name="Barisal Gadgets",
            slug="barisal-gadgets",
            currency="BDT",
            timezone="Asia/Dhaka",
        )
        self.product_a = Product.objects.create(
            business=self.business_a,
            name="Apex Pegasus Runner Shoe",
            sku="APX-PEG-01",
        )

    # ─────────────────────────────────────────────────────────────
    # Feature 1: Business Profile
    # ─────────────────────────────────────────────────────────────

    def test_feature_01_set_and_get_business_profile(self):
        profile = BusinessProfileData(
            name="Apex Retail Dhaka",
            description="Premium footwear and activewear brand in Bangladesh.",
            industry="Apparel & Footwear",
            operating_regions=["Dhaka", "Chittagong", "Sylhet"],
            target_customers="Urban fitness enthusiasts and professionals aged 20-45",
            operating_model={"sales_channels": ["WEB", "STORE"], "fulfillment": "COURIER"},
            ai_context_summary="Apex delivers quality activewear with fast regional delivery.",
        )
        mem = set_business_profile(self.business_a, profile)
        self.assertEqual(mem.business, self.business_a)
        self.assertEqual(mem.memory_type, "BUSINESS_PROFILE")

        retrieved = get_business_profile(self.business_a)
        self.assertEqual(retrieved["name"], "Apex Retail Dhaka")
        self.assertEqual(retrieved["industry"], "Apparel & Footwear")
        self.assertIn("Dhaka", retrieved["operating_regions"])

    def test_feature_01_business_profile_tenant_isolation(self):
        with self.assertRaises(TenantIsolationError):
            set_business_profile(None, BusinessProfileData(  # type: ignore
                name="Null", description="", industry="", operating_regions=[],
                target_customers="", operating_model={}, ai_context_summary=""
            ))

    # ─────────────────────────────────────────────────────────────
    # Feature 2: Business Policies
    # ─────────────────────────────────────────────────────────────

    def test_feature_02_set_and_get_business_policies(self):
        set_business_policy(
            business=self.business_a,
            policy_category="DISCOUNT_POLICY",
            title="Seasonal Promo Maximums",
            content="Discounts must never exceed 30% without regional manager approval.",
            applicability="ALL_SALES",
        )
        policies = get_active_policies(self.business_a, policy_category="DISCOUNT_POLICY")
        self.assertEqual(len(policies), 1)
        self.assertEqual(policies[0].metadata.get("applicability"), "ALL_SALES")

    # ─────────────────────────────────────────────────────────────
    # Feature 3: Product Knowledge
    # ─────────────────────────────────────────────────────────────

    def test_feature_03_set_and_get_product_knowledge(self):
        set_product_knowledge(
            business=self.business_a,
            product=self.product_a,
            knowledge_type="SIZING_GUIDE",
            title="Pegasus Runner Size Chart",
            content="True to size. For wider feet, choose one half-size larger.",
        )
        know = get_product_knowledge(self.business_a, self.product_a.id)
        self.assertEqual(len(know), 1)
        self.assertEqual(know[0].subject_entity_id, self.product_a.id)
        self.assertIn("True to size", know[0].content)

    # ─────────────────────────────────────────────────────────────
    # Feature 4: Delivery Policy
    # ─────────────────────────────────────────────────────────────

    def test_feature_04_set_and_get_delivery_policy(self):
        del_data = DeliveryPolicyData(
            coverage_zones=["Inside Dhaka", "Sub-Dhaka", "Outside Dhaka"],
            sla_hours={"Inside Dhaka": 24, "Sub-Dhaka": 48, "Outside Dhaka": 72},
            charges={"Inside Dhaka": 60.0, "Outside Dhaka": 120.0},
            courier_preferences=["Pathao", "Steadfast"],
            cod_rules={"enabled": True, "max_amount": 10000.0},
            failed_delivery_handling="Call customer twice before scheduling return.",
        )
        set_delivery_policy(self.business_a, del_data)
        retrieved = get_delivery_policy(self.business_a)
        self.assertEqual(retrieved["sla_hours"]["Inside Dhaka"], 24)
        self.assertEqual(retrieved["charges"]["Outside Dhaka"], 120.0)
        self.assertIn("Pathao", retrieved["courier_preferences"])

    # ─────────────────────────────────────────────────────────────
    # Feature 5: Return & Refund Policy
    # ─────────────────────────────────────────────────────────────

    def test_feature_05_set_and_get_return_policy(self):
        ret_data = ReturnRefundPolicyData(
            return_window_days=7,
            eligible_conditions=["Unworn", "Original box intact", "Invoice present"],
            non_returnable_conditions=["Underwear", "Discount items above 50%"],
            refund_methods=["ORIGINAL_PAYMENT", "BKASH", "STORE_CREDIT"],
            replacement_allowed=True,
            cancellation_cutoff_hours=4,
        )
        set_return_refund_policy(self.business_a, ret_data)
        retrieved = get_return_refund_policy(self.business_a)
        self.assertEqual(retrieved["return_window_days"], 7)
        self.assertTrue(retrieved["replacement_allowed"])
        self.assertIn("BKASH", retrieved["refund_methods"])

    # ─────────────────────────────────────────────────────────────
    # Feature 6: Brand Tone & Vocabulary Validation
    # ─────────────────────────────────────────────────────────────

    def test_feature_06_brand_tone_and_restricted_words(self):
        tone_data = BrandToneData(
            primary_tone="Professional, polite, empathetic",
            style_guidelines=["Use active voice", "Keep sentences concise"],
            preferred_terms=["Valued Customer", "Express Delivery", "Authentic Guarantee"],
            restricted_words=["guarantee 100%", "cheap", "no problem", "never fails"],
            channel_overrides={
                "INSTAGRAM": {"primary_tone": "Energetic, engaging, friendly"},
            },
        )
        set_brand_tone(self.business_a, tone_data)
        retrieved = get_brand_tone(self.business_a)
        self.assertIn("polite", retrieved["primary_tone"])

        # Validate channel override
        ig_tone = get_brand_tone(self.business_a, channel="INSTAGRAM")
        self.assertIn("Energetic", ig_tone["primary_tone"])

        # Check restricted words
        violations = validate_text_against_brand_tone(
            self.business_a,
            "Our shoe is cheap and we guarantee 100% satisfaction!",
        )
        self.assertEqual(len(violations), 2)
        self.assertIn("cheap", violations)
        self.assertIn("guarantee 100%", violations)

    # ─────────────────────────────────────────────────────────────
    # Feature 7: Support Knowledge
    # ─────────────────────────────────────────────────────────────

    def test_feature_07_support_knowledge_and_troubleshooting(self):
        set_support_knowledge(
            business=self.business_a,
            category="DELIVERY_DELAY",
            question_or_topic="What to do if order delayed past 48 hours in Dhaka",
            approved_answer="Apologize to customer, contact courier dispatcher, and offer 50 BDT credit voucher.",
            troubleshooting_tree={
                "check_tracking": True,
                "if_held_at_hub": "Escalate to courier rep",
            },
            escalation_team="LOGISTICS_TIER_2",
        )
        know = get_support_knowledge(self.business_a, category="DELIVERY_DELAY")
        self.assertEqual(len(know), 1)
        self.assertEqual(know[0].metadata.get("escalation_team"), "LOGISTICS_TIER_2")

    # ─────────────────────────────────────────────────────────────
    # Feature 8: Business Goals
    # ─────────────────────────────────────────────────────────────

    def test_feature_08_business_goals_prioritized(self):
        set_business_goal(
            business=self.business_a,
            name="Reduce Delivery Failure Rate",
            category="LOGISTICS",
            priority="HIGH",
            target_value="< 5%",
            timeframe="Q3 2026",
        )
        set_business_goal(
            business=self.business_a,
            name="Increase Instagram ROAS",
            category="MARKETING",
            priority="MEDIUM",
            target_value="> 3.5",
            timeframe="Q3 2026",
        )
        goals = get_active_business_goals(self.business_a)
        self.assertEqual(len(goals), 2)
        # High priority should be first
        self.assertEqual(goals[0].priority, "HIGH")

    # ─────────────────────────────────────────────────────────────
    # Feature 9: Historical Decisions & Repeat Prevention
    # ─────────────────────────────────────────────────────────────

    def test_feature_09_historical_decision_repeat_prevention(self):
        now = timezone.now()
        record_historical_decision(
            business=self.business_a,
            decision_type="COURIER_ROUTING",
            title="Pause RedX in Gazipur",
            rationale="RedX failure rate exceeded 22% in Gazipur during June.",
            outcome="REJECTED",  # Trying RedX was rejected/failed
            target_entity_type="COURIER",
            target_entity_id=901,
            decided_by=self.user,
            decided_at=now,
        )
        conflict = check_repeat_decision_conflict(
            business=self.business_a,
            decision_type="COURIER_ROUTING",
            target_entity_type="COURIER",
            target_entity_id=901,
        )
        self.assertIsNotNone(conflict)
        self.assertEqual(conflict.outcome, "REJECTED")
        self.assertIn("RedX", conflict.title)

    # ─────────────────────────────────────────────────────────────
    # Feature 10: Approved Suggestions & Governance Gate
    # ─────────────────────────────────────────────────────────────

    def test_feature_10_promote_approved_suggestion_happy_path(self):
        now = timezone.now()
        rec = AiRecommendation.objects.create(
            business=self.business_a,
            recommendation_type="COURIER_OPTIMIZATION",
            title="Route Gazipur to Steadfast",
            description="Shift 50% of Gazipur volume to Steadfast.",
            status="APPROVED",
            generated_at=now,
        )
        approved_sugg = promote_approved_suggestion(
            business=self.business_a,
            recommendation=rec,
            approved_by=self.user,
            approved_at=now,
        )
        self.assertIsNotNone(approved_sugg.id)
        self.assertEqual(approved_sugg.business, self.business_a)
        self.assertEqual(approved_sugg.approved_by, self.user)
        self.assertEqual(approved_sugg.status, "APPROVED")

    def test_feature_10_promote_unapproved_suggestion_raises_error(self):
        now = timezone.now()
        unapproved_rec = AiRecommendation.objects.create(
            business=self.business_a,
            recommendation_type="BUDGET_CHANGE",
            title="Double Meta Budget",
            description="Scale Meta campaign budget to 50k.",
            status="SUGGESTED",  # NOT APPROVED!
            generated_at=now,
        )
        # Attempting to promote without human approval must raise UnapprovedMemoryPromotionError
        with self.assertRaises(UnapprovedMemoryPromotionError):
            promote_approved_suggestion(
                business=self.business_a,
                recommendation=unapproved_rec,
                approved_by=None,
                approved_at=None,
            )

    # ─────────────────────────────────────────────────────────────
    # Phase 4 Mutation Audits: Cross-Tenant Promotion & Punctuation
    # ─────────────────────────────────────────────────────────────

    def test_mutation_cross_tenant_promotion_is_blocked(self):
        now = timezone.now()
        rec_b = AiRecommendation.objects.create(
            business=self.business_b,  # Business B
            recommendation_type="CAMPAIGN_EXPANSION",
            title="Barisal Ad Campaign",
            description="Expand to Barisal",
            status="APPROVED",
            generated_at=now,
        )
        # Attempting to promote Business B's recommendation under Business A must raise TenantIsolationError
        with self.assertRaises(TenantIsolationError):
            promote_approved_suggestion(
                business=self.business_a,  # Business A target
                recommendation=rec_b,
                approved_by=self.user,
                approved_at=now,
            )

    def test_mutation_brand_tone_with_punctuation_and_caps(self):
        tone_data = BrandToneData(
            primary_tone="Professional",
            style_guidelines=[],
            preferred_terms=[],
            restricted_words=["cheap", "never fails"],
            channel_overrides={},
        )
        set_brand_tone(self.business_a, tone_data)
        violations = validate_text_against_brand_tone(
            self.business_a,
            "This product is CHEAP! And it NEVER FAILS.",
        )
        self.assertEqual(len(violations), 2)
        self.assertIn("cheap", violations)
        self.assertIn("never fails", violations)


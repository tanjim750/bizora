from django.conf import settings
from django.test import TestCase

from app.events.dispatcher import dispatch, subscribe
from app.models import AiRecommendation


class EventMock:
    def __init__(self, name, payload=None):
        self.name = name
        self.payload = payload or {}


class P2RegressionTests(TestCase):
    """
    Automated regression tests asserting correct/secure behavior for P2 issues.
    Running these against the current unfixed code demonstrates reproduction of the bugs.
    """

    def test_mod_001_drf_default_permissions_not_is_authenticated(self):
        """
        MOD-001: REST_FRAMEWORK settings must define DEFAULT_PERMISSION_CLASSES including IsAuthenticated.
        Expected failure: AssertionError: 'DEFAULT_PERMISSION_CLASSES' missing from settings.REST_FRAMEWORK
        """
        drf_settings = getattr(settings, "REST_FRAMEWORK", {})
        self.assertIn(
            "DEFAULT_PERMISSION_CLASSES",
            drf_settings,
            "MOD-001 Defect: REST_FRAMEWORK settings omit DEFAULT_PERMISSION_CLASSES, defaulting to AllowAny!",
        )
        self.assertIn(
            "rest_framework.permissions.IsAuthenticated",
            drf_settings.get("DEFAULT_PERMISSION_CLASSES", []),
            "MOD-001 Defect: Default DRF permission is not IsAuthenticated!",
        )

    def test_mod_002_ai_recommendation_confidence_range_unconstrained(self):
        """
        MOD-002: AiRecommendation model must have a CheckConstraint restricting 0.0 <= confidence <= 1.0.
        Expected failure: AssertionError: No CheckConstraint found on AiRecommendation for confidence range
        """
        constraints = AiRecommendation._meta.constraints
        check_constraint_names = [c.name for c in constraints if hasattr(c, "check")]
        self.assertTrue(
            any("confidence" in name.lower() for name in check_constraint_names),
            "MOD-002 Defect: AiRecommendation has no database CheckConstraint enforcing 0.0 <= confidence <= 1.0!",
        )

    def test_mod_003_support_ai_policy_omission(self):
        """
        MOD-003: Customer Support AI pipeline must enforce mandatory policy retrieval for refund inquiries.
        Expected failure: AssertionError: No policy retrieval module/hook configured for Customer Support AI
        """
        # Invariant: Support context builder must implement policy retrieval hook
        from app.models import KnowledgeDocument

        has_policy_hook = hasattr(KnowledgeDocument, "get_active_policies_for_intent")
        self.assertTrue(
            has_policy_hook,
            "MOD-003 Defect: Support AI context retrieval lacks intent-driven policy injection hook!",
        )

    def test_mod_004_event_dispatcher_allows_duplicate_subscriptions(self):
        """
        MOD-004: Subscribing the same handler multiple times creates duplicate invocations in in-memory dispatcher.
        Expected failure: AssertionError: Handler was invoked 3 times instead of 1
        """
        invocations = []

        def idempotent_handler(event):
            invocations.append(1)

        # Register handler 3 times
        subscribe("test.duplicate.event", idempotent_handler)
        subscribe("test.duplicate.event", idempotent_handler)
        subscribe("test.duplicate.event", idempotent_handler)

        with self.captureOnCommitCallbacks(execute=True):
            dispatch(EventMock("test.duplicate.event", {}))

        # Desired invariant: Handler subscriptions must be deduplicated
        self.assertEqual(
            len(invocations),
            1,
            f"MOD-004 Defect: Handler was executed {len(invocations)} times because subscriptions are not deduplicated!",
        )

    def test_mod_005_graph_traversal_cycle_trap(self):
        """
        MOD-005: Graph traversal without visited tracking or depth limits hangs on cyclic graphs.
        Expected failure: AssertionError: Graph traversal algorithm allows infinite cycles or exceeds depth limit
        """
        import networkx as nx

        G = nx.DiGraph()
        G.add_edge("A", "B")
        G.add_edge("B", "A")  # Cycle: A -> B -> A

        from app.services.graph import safe_traverse

        path = safe_traverse(G, "A", max_depth=10)
        # Desired invariant: Visited set ensures each node visited at most once
        unique_nodes = set(path)
        self.assertEqual(
            len(path),
            len(unique_nodes),
            f"MOD-005 Defect: Graph traversal on cycle expanded {len(path)} steps for {len(unique_nodes)} unique nodes without cycle prevention!",
        )

    def test_mod_006_settings_insecure_fallback_secret_key(self):
        """
        MOD-006: In production settings (DEBUG=False), missing SECRET_KEY env var must raise ImproperlyConfigured.
        Expected failure: AssertionError: Settings allowed insecure fallback secret key
        """
        secret_key = settings.SECRET_KEY
        self.assertFalse(
            secret_key.startswith("django-insecure"),
            "MOD-006 Defect: SECRET_KEY is using a predictable django-insecure fallback key!",
        )

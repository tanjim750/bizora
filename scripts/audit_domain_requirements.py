#!/usr/bin/env python3
"""Rebuild a human-reviewed requirements inventory; this does not infer test coverage.

The assessments below are explicit review decisions, not completion detection from model
names. AST checks only ensure that cited implementation and test symbols still exist.
Run after reviewing changes to the source specifications. No database is accessed.
"""
import ast
from collections import Counter
from functools import lru_cache
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'docs/implementations'
SPECS = ('business-data', 'identity-resulation', 'business-oparations')

# Group evidence is deliberately shared: these are integration tests across a group,
# not an assertion that every sentence has an independent acceptance test.
GROUPS = {
 'Product': ('app/domains/data.py:ingest,_product_children,update_variant', 'app/test_domains.py:CanonicalDataTests,MappingTests,CatalogAndFinancialProjectionTests;app/test_domain_completion.py:ProductDeduplicationTests'),
 'Customer': ('app/domains/data.py:_customer_children,_timeline;app/domains/queries.py:lookup', 'app/test_domains.py:CanonicalDataTests;app/test_domain_completion.py:OperationalCompletionTests,DocumentedRepresentationTests,RecoveredTimelineTests'),
 'Order': ('app/domains/data.py:_order,transition', 'app/test_domains.py:CanonicalDataTests,AdditionalIntegrityTests'),
 'Payment': ('app/domains/data.py:_refund,_refund_payment,transition', 'app/test_domains.py:CanonicalDataTests,PostgresConcurrencyTests;app/test_domain_completion.py:CanonicalCompletionTests'),
 'Communication': ('app/domains/data.py:ingest;app/domains/operations.py:mark_read;app/domains/contracts.py:prepare_operation', 'app/test_domains.py:CanonicalDataTests,AdditionalIntegrityTests;app/test_domain_completion.py:DocumentedRepresentationTests,ExternalContractTests'),
 'Customer Support': ('app/domains/operations.py:assign,handover,set_priority;app/domains/projections.py:support_context', 'app/test_domains.py:SupportOperationTests;app/test_domain_completion.py:OperationalCompletionTests,DocumentedRepresentationTests'),
 'Marketing': ('app/domains/data.py:ingest;app/domains/projections.py:retargeting_context', 'app/test_domains.py:CanonicalDataTests,DocumentationBoundaryTests;app/test_domain_completion.py:CallbackAndConversionTests,OperationalCompletionTests'),
 'Website Behavior': ('app/domains/data.py:ingest;app/domain_views.py:JourneyView;app/domains/identity.py:link_anonymous', 'app/test_domain_completion.py:CanonicalCompletionTests,OperationalCompletionTests,DocumentedRepresentationTests,RecoveredTimelineTests'),
 'Courier': ('app/domains/data.py:ingest,transition;app/domains/contracts.py:prepare_operation', 'app/test_domains.py:CanonicalDataTests,CustomerReferenceContinuityTests;app/test_domain_completion.py:ExternalContractTests,CrossSourceAndQueueContractTests'),
 'Calling': ('app/domains/data.py:ingest,transition;app/domains/operations.py:schedule_callback;app/domains/contracts.py:prepare_operation', 'app/test_domains.py:CanonicalDataTests;app/test_domain_completion.py:CanonicalCompletionTests,DocumentedRepresentationTests,CallbackAndConversionTests,ExternalContractTests'),
 'Canonical Identity': ('app/domains/identity.py:canonical,set_status', 'app/test_domains.py:IdentityTests;app/test_domain_completion.py:IdentityCompletionTests'),
 'External Identity': ('app/domains/identity.py:register,enrich_external;app/domains/common.py:normalize_contact', 'app/test_domains.py:IdentityTests;app/test_domain_completion.py:IdentityCompletionTests'),
 'Identity Linking': ('app/domains/identity.py:_link,link,unlink,set_status', 'app/test_domains.py:IdentityTests,AnonymousIdentityLinkTests;app/test_domain_completion.py:IdentityCompletionTests'),
 'Cross-Source Matching': ('app/domains/identity.py:resolve,resolve_many', 'app/test_domains.py:IdentityTests;app/test_domain_completion.py:IdentityCompletionTests,ProductDeduplicationTests'),
 'Anonymous Identity Linking': ('app/domains/identity.py:link_anonymous', 'app/test_domains.py:AnonymousIdentityLinkTests;app/test_domain_completion.py:IdentityCompletionTests,RecoveredTimelineTests'),
 'Merge Detection': ('app/domains/identity.py:detect_merges,review_merge,execute_merge', 'app/test_domains.py:IdentityTests;app/test_domain_completion.py:ProductDeduplicationTests'),
 'Identity Conflict Resolution': ('app/domains/identity.py:conflict,review_conflict,validate_links,resolve_many', 'app/test_domains.py:IdentityTests;app/test_domain_completion.py:IdentityCompletionTests'),
 'Identity History': ('app/domains/identity.py:history;app/domain_views.py:IdentityView', 'app/test_domains.py:IdentityTests,AnonymousIdentityLinkTests;app/test_domain_completion.py:PersistedGraphContractTests,RecoveredTimelineTests'),
 'Business Overview': ('app/domains/projections.py:overview,authority_context', 'app/test_domains.py:SupportOperationTests,DomainAPITests;app/test_domain_completion.py:ExternalContractTests'),
 'Customer 360': ('app/domains/projections.py:customer360,graph_context', 'app/test_domains.py:SupportOperationTests,CustomerReferenceContinuityTests;app/test_domain_completion.py:OperationalCompletionTests,PersistedGraphContractTests'),
 'Product Operations': ('app/domains/projections.py:detail,graph_context;app/domains/data.py:update_variant', 'app/test_domains.py:MappingTests,CatalogAndFinancialProjectionTests;app/test_domain_completion.py:ProductDeduplicationTests,PersistedGraphContractTests'),
 'Order Operations': ('app/domains/projections.py:detail,graph_context;app/domains/data.py:transition', 'app/test_domains.py:CanonicalDataTests,DomainAPITests;app/test_domain_completion.py:PersistedGraphContractTests'),
 'Payment Operations': ('app/domains/projections.py:detail,financial_timeline', 'app/test_domains.py:CanonicalDataTests,CatalogAndFinancialProjectionTests'),
 'Unified Inbox': ('app/domain_views.py:ResourceList;app/domains/projections.py:support_context;app/domains/queries.py:conversation_search', 'app/test_domains.py:DomainAPITests;app/test_domain_completion.py:OperationalCompletionTests'),
 'Support Queue': ('app/domain_views.py:SupportQueueView', 'app/test_domains.py:DomainAPITests;app/test_domain_completion.py:CrossSourceAndQueueContractTests'),
 'Conversation Assignment': ('app/domains/operations.py:assign;app/domain_views.py:AssignmentView', 'app/test_domains.py:SupportOperationTests,AdditionalIntegrityTests,DomainAPITests'),
 'AI ↔ Human Handover': ('app/domains/operations.py:handover;app/domains/projections.py:support_context', 'app/test_domains.py:SupportOperationTests,DomainAPITests;app/test_domain_completion.py:OperationalCompletionTests'),
 'Marketing Operations': ('app/domains/projections.py:detail,authority_context;app/domains/operations.py:review_action', 'app/test_domains.py:CanonicalDataTests,SupportOperationTests,DocumentationBoundaryTests;app/test_domain_completion.py:ExternalContractTests'),
 'Website Performance': ('app/domain_views.py:WebsitePerformanceView;app/domains/projections.py:authority_context', 'app/test_domains.py:DomainAPITests;app/test_domain_completion.py:CanonicalCompletionTests,DocumentedRepresentationTests'),
 'Delivery Operations': ('app/domains/projections.py:detail,authority_context;app/domains/contracts.py:prepare_operation', 'app/test_domains.py:CanonicalDataTests,DomainAPITests;app/test_domain_completion.py:ExternalContractTests'),
 'Call Operations': ('app/domains/projections.py:detail;app/domains/contracts.py:prepare_operation', 'app/test_domains.py:CanonicalDataTests,DomainAPITests;app/test_domain_completion.py:DocumentedRepresentationTests,ExternalContractTests'),
}

# Conservative defaults: canonical storage/service requirements can be complete;
# operational screen requirements remain partial because no frontend exists.
OVERRIDES = {}

def assess(group, names, status, category, note):
    for name in names.split('|'):
        OVERRIDES[(group, name)] = (status, category, note)

for group, name in [('Product', 'Product Normalization'), ('Order', 'Order Normalization'), ('Payment', 'Payment Normalization'), ('Marketing', 'Campaign Normalization')]:
    assess(group, name, 'PARTIAL', 'B', 'Canonical envelope validated and replay-safe; only explicitly simulated adapters exist. Integrations owns real provider schemas, credentials, signatures and transport.')
assess('Product', 'Product Deduplication', 'PARTIAL', 'A', 'Source-reference/replay and parent+SKU variant upsert work. Opt-in verified product SKU resolution and review candidates exist; arbitrary new product intake without a source reference does not automatically deduplicate by SKU. SKU is not globally unique.')
assess('Communication', 'Channel Abstraction|Incoming Message Processing|Outgoing Message Processing|Communication Connectors', 'PARTIAL', 'B', 'Canonical channel/direction/message contract and explicit mock transport work; pending outbound request preparation does not send. Real connector intake/delivery remains owned by Integrations.')
assess('Customer Support', 'Suggested Reply Context', 'PARTIAL', 'B', 'Canonical customer, order, messages, notes and history context is available. Policy retrieval and generated replies explicitly return UNAVAILABLE (Memory/AI).')
assess('Marketing', 'Marketing Platform Support', 'PARTIAL', 'B', 'Platform-neutral hierarchy/source association and payload metadata exist; real platform adapters require Integrations.')
assess('Marketing', 'Retargeting Context', 'PARTIAL', 'B', 'Observed customer sessions/events/conversions are exposed; abandonment/interest scoring and audience recommendations require BI/AI and are unavailable.')
assess('Website Behavior', 'Analytics Integration', 'PARTIAL', 'B', 'Validated canonical event/session intake exists; no live GA4 or other analytics adapter is fabricated.')
assess('Courier', 'Shipment Submission|Shipment Tracking|Shipment Cancellation|Courier Provider Support', 'PARTIAL', 'B', 'Canonical states, observed tracking events and non-executing outbound preparation exist. Live submission/polling/cancellation/acknowledgements require Integrations.')
assess('Calling', 'Incoming Calls|Outgoing Calls|Calling Platform Integration', 'PARTIAL', 'B', 'Observed incoming/outgoing records, events and pending outgoing contract work; receiving/initiating live calls requires Integrations.')
assess('Calling', 'Call Recording', 'PARTIAL', 'B', 'Provider recording reference is stored privately; authorized recording transport returns UNAVAILABLE. No recording download/access service exists.')
assess('Canonical Identity', 'Identity Status Management', 'PARTIAL', 'C', 'ACTIVE/INACTIVE/SUPERSEDED and link invalidation are tested. MERGED state requires a real downstream-safe consolidation contract; assigning a fake merge status is rejected.')
assess('Identity Linking', 'Match Type Tracking', 'PARTIAL', 'C', 'EXACT/DETERMINISTIC/MANUAL/ANONYMOUS_TO_KNOWN are executed and audited. Actual MERGED provenance waits for safe consolidation.')
assess('Identity Linking', 'Confidence Tracking', 'PARTIAL', 'A', 'Exact/manual link storage and range validation exist; links currently use confidence=1. No graded confidence policy is implemented or invented.')
assess('Cross-Source Matching', 'Deterministic Multi-Field Matching', 'PARTIAL', 'A', '2–20 independently verified CUSTOMER identifiers must corroborate one customer atomically; contradictions and partial matches roll back. This is an explicit corroboration rule, not a configurable arbitrary attribute-combination engine.')
assess('Cross-Source Matching', 'Cross-Platform Product Matching', 'PARTIAL', 'A', 'Source references and explicit manager-verified SKU rule are implemented; ambiguous SKU creates conflict. General configurable product matching rules are not implemented.')
assess('Anonymous Identity Linking', 'Identity Transition Detection', 'PARTIAL', 'B', 'Purchase/order and verified LOGIN/SIGNUP/FORM_SUBMISSION command paths work. Automatic provider checkout/communication event dispatch requires an authenticated external adapter; no background detector is claimed.')
assess('Anonymous Identity Linking', 'Attribution Continuity', 'PARTIAL', 'B', 'Original visitor/session/event/campaign links and timestamps survive recovery. This supplies attribution inputs, not BI attribution decisions.')
assess('Merge Detection', 'Merge Confidence', 'PARTIAL', 'A', 'Shared verified-contact candidates retain deterministic confidence; product SKU candidates intentionally keep unknown confidence. A calibrated graded confidence policy needs a team decision.')
assess('Merge Detection', 'Merge Candidate Review', 'PARTIAL', 'C', 'Pending/approved/rejected review works. MERGED terminal outcome depends on blocked execution; approval never silently merges.')
assess('Merge Detection', 'Canonical Identity Consolidation|Relationship Preservation', 'BLOCKED', 'C', 'execute_merge refuses with BI_GRAPH_AI_MERGE_CONTRACT. BI/Graph/AI owners must agree generic-reference redirect/reprojection and audit preservation before destructive consolidation.')
assess('Identity History', 'Merge History', 'BLOCKED', 'C', 'Candidate/review/block attempts are audited. No real completed-merge history exists because consolidation is blocked; no fake merge record is emitted.')

# These operational requirements depend on actual authoritative outputs. Local persisted
# reads/fallbacks are present, so PARTIAL/B distinguishes them from a missing local seam.
for group, names in {
 'Business Overview': 'Cross-Domain Summary|Key Business Indicators|Active Business Issues|Recommendation Summary',
 'Customer 360': 'Website Journey|Marketing Context|Customer Graph View|AI Customer Context',
 'Product Operations': 'Product Performance Context|Product Marketing Context|Product Support Context|Product Graph View',
 'Order Operations': 'Conversation Context|Campaign Attribution Context|Order Graph View',
 'Unified Inbox': 'AI Suggested Replies',
 'Support Queue': 'Overdue Support Detection|AI Escalation Signals|Queue Metrics',
 'AI ↔ Human Handover': 'Conversation Summary|Context Preservation|Customer Transparency',
 'Marketing Operations': 'Campaign Metrics|Attributed Revenue View|Campaign Performance Trends|Campaign Issue Indicators|Cross-Domain Outcome View|AI Marketing Recommendations|Suggested Marketing Actions|Approval Flow',
 'Website Performance': 'Traffic Overview|Traffic Source Performance|Conversion Funnel View|Cart Abandonment View|Checkout Drop-Off View|Landing Page Performance|Product Behavior View|Device & Browser Performance|Experience Signals|Website Issues|AI Website Recommendations',
 'Delivery Operations': 'Courier Performance Context|Regional Delivery Context|AI Delivery Recommendations|Suggested Courier Actions',
 'Call Operations': 'Recording Access|AI Call Summary',
}.items():
    assess(group, names, 'PARTIAL', 'B', 'Canonical/persisted evidence can be read and absent capabilities are explicit. Full documented behavior needs the external BI/Graph/AI/Memory/Configuration/Integrations owner; no generated result or full operational screen is claimed.')

# Narrower notes prevent a generic persisted reader from being mistaken for the feature.
assess('Customer 360', 'Customer Graph View', 'PARTIAL', 'B', 'Tenant-safe persisted one-hop graph context exists; full customer relationship/journey visualization and Graph generation/traversal remain unavailable.')
assess('Product Operations', 'Product Graph View', 'PARTIAL', 'B', 'Persisted one-hop product graph read only; no full graph journey/traversal or frontend.')
assess('Order Operations', 'Order Graph View', 'PARTIAL', 'B', 'Persisted one-hop order graph read only; no full graph journey/traversal or frontend.')
assess('Unified Inbox', 'AI Suggested Replies', 'PARTIAL', 'B', 'support_context supplies actual conversation/customer/order evidence and an explicit unavailable reply/policy capability; AI text generation is not implemented.')
assess('Support Queue', 'Overdue Support Detection', 'PARTIAL', 'B', 'Queue exposes an unavailable Configuration-owned response/resolution policy contract. No threshold, SLA clock or overdue classification is invented.')
assess('AI ↔ Human Handover', 'Customer Transparency', 'PARTIAL', 'B', 'Handover reason/history and human summary are persisted; customer-facing notification transport/policy and UI are absent.')
assess('Marketing Operations', 'Approval Flow', 'PARTIAL', 'B', 'Manager review checks current verified tenant-safe evidence and records approval/rejection. Execution and outcome tracking require an external execution contract; no execution is claimed.')
assess('Call Operations', 'AI Call Summary', 'PARTIAL', 'B', 'Imported/provider summary text is visible; local AI generation is unavailable.')


@lru_cache(maxsize=None)
def symbol_links(spec):
    links = []
    for entry in spec.split(';'):
        path, names = entry.split(':')
        tree = ast.parse((ROOT / path).read_text())
        symbols = {node.name: node.lineno for node in ast.walk(tree) if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))}
        for name in names.split(','):
            if name not in symbols:
                raise ValueError(f'Missing evidence: {path}:{name}')
            links.append({'path': path, 'symbol': name, 'line': symbols[name]})
    return links


def build():
    records, used = [], set()
    for domain in SPECS:
        path = f'docs/implementations/features/{domain}.md'
        lines = (ROOT / path).read_text().splitlines()
        group = None
        group_no = 0
        feature_no = 0
        for index, line in enumerate(lines):
            match = re.match(r'### (\d+)\. (.+)', line)
            if match:
                group_no, group = int(match[1]), match[2]
                feature_no = 0
            feature = re.match(r'\* \*\*(.+?)\*\*$', line)
            if not feature:
                continue
            name = feature[1]
            feature_no += 1
            description = []
            for text in lines[index+1:]:
                if not text.strip() and description:
                    break
                if text.strip():
                    description.append(text.strip())
            default = ('PARTIAL', 'A', 'Backend list/detail/context/commands are available as evidenced below. No operational frontend screen exists; a complete documented view/workflow is not claimed.') if domain == 'business-oparations' else ('COMPLETE', 'A', 'Documented canonical storage/service behavior is implemented and covered by the cited group integration tests. This does not imply a live provider connection or generated analytics.')
            if group == 'Conversation Assignment':
                default = ('COMPLETE', 'A', 'Documented assignment foundation, history, release/reassign, metadata and callable future routing hook are tested; no automatic routing policy is claimed.')
            key = (group, name)
            status, category, note = OVERRIDES.get(key, default)
            if key in OVERRIDES:
                used.add(key)
            code, tests = GROUPS[group]
            records.append({'id': f'{domain}:{group_no:02}.{feature_no:02}', 'domain': domain, 'group': group,
                'feature': name, 'requirement': {'path': path, 'line': index+1, 'description': ' '.join(description)},
                'status': status, 'category': category, 'assessment': note,
                'code_evidence': symbol_links(code), 'test_evidence': symbol_links(tests)})
    assert len(records) == 298, f'Specification changed: expected 298, got {len(records)}'
    assert len(set((r['domain'], r['group']) for r in records)) == 31
    assert set(OVERRIDES) == used, f'Unmatched assessments: {set(OVERRIDES) - used}'
    return records


def main():
    records = build()
    counts = Counter(r['status'] for r in records)
    payload = {'scope': 'Full documented feature statuses; backend tests alone do not complete operational frontend views.',
        'total': len(records), 'status_counts': dict(counts), 'requirements': records}
    (OUT / 'domain-requirements-audit.json').write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n')
    text = ['# Bizora: 298 documented subfeature audit', '', '24 October 2026. Generated from explicit reviewed assessments in `scripts/audit_domain_requirements.py`.', '',
        'Status evaluates the full documented subfeature, including a screen where the Operations specification calls for a view. Backend availability alone does not complete that view.', '',
        '**A:** local work. **B:** local read/input/request contract exists; external domain completes the behavior. **C:** destructive or authoritative behavior cannot safely proceed until the named owner contract exists.', '',
        'Categories describe responsibility, not completion. COMPLETE/A rows are already done. PARTIAL/A rows below remain honest local limitations. No model-presence heuristic or passing-test count upgrades status.', '',
        'Tests cited under each group are actual integration classes; they are not a claim of a dedicated acceptance test for every sentence. JSON retains every original requirement description and exact evidence symbol line.', '',
        f'**Total: {len(records)}.** ' + '; '.join(f'{key}: {value}' for key, value in sorted(counts.items())) + '.', '',
        'External blockers: Integrations (transport/provider schemas), BI (authoritative calculations/attribution), Graph (building/traversal/merge redirect), AI (generation/execution), Memory (policies), Configuration (SLA/escalation policy). UI implementation is local unfinished work, not a fabricated external blocker.', '']
    previous = None
    for row in records:
        key = (row['domain'], row['group'])
        if key != previous:
            text += ['', f"## {row['domain']} / {row['group']}", '']
            for label, evidence in [('Implementation', row['code_evidence']), ('Tests (group integration evidence)', row['test_evidence'])]:
                text.append(label + ': ' + ', '.join(f"[`{e['path']}:{e['symbol']}`](../../{e['path']}#L{e['line']})" for e in evidence) + '.')
            text += ['', '| Requirement | Status / category | Evidence assessment and remaining behavior |', '| --- | --- | --- |']
            previous = key
        req = row['requirement']
        text.append(f"| [{row['feature']}](features/{row['domain']}.md#L{req['line']}) | **{row['status']} / {row['category']}** | {row['assessment']} |")
    (OUT / 'my-domains-requirements-audit.md').write_text('\n'.join(text) + '\n')
    print(json.dumps({'total': len(records), 'statuses': dict(counts), 'categories': dict(Counter(r['category'] for r in records))}))


if __name__ == '__main__':
    main()

from .catalog import CROSS_DOMAIN
from .findings import issue_data, issues_query, with_issue_evidence


def cross_domain(business, config, evidence, now):
    results = {key: {'key': key, 'domains': list(CROSS_DOMAIN[key]), 'status': 'NO_VERIFIED_FINDING', 'issues': []}
               for key in config['cross_domain']}
    rows = list(with_issue_evidence(issues_query(business.pk, {}, now, config))[:501])
    evidence.prime_findings(rows)
    for row in rows[:500]:
        metadata = row.metadata if isinstance(row.metadata, dict) else {}
        scenarios = metadata.get('monitoring_scenarios', [])
        if not isinstance(scenarios, list):
            continue
        valid_evidence = evidence.issue_evidence(row)
        links = [r for item in valid_evidence for r in item['references']
                 if r['kind'] == 'relationships' and r['relationship_source'] == 'DETERMINISTIC']
        if not links:
            continue
        linked_domains = {ref[side]['domain'] for ref in links for side in ('source', 'target')}
        for item in valid_evidence:
            for reference in item['references']:
                if reference['kind'] == 'snapshots':
                    linked_domains.add(reference['domain'])
        # BI declares the supported scenario; an existing deterministic relationship grounds it.
        # Monitoring never discovers causation from coincident metrics or creates a relationship.
        for key in scenarios:
            if not isinstance(key, str) or key not in results or not set(CROSS_DOMAIN[key]) <= linked_domains:
                continue
            results[key]['status'] = 'REQUIRES_ATTENTION'
            results[key]['issues'].append({**issue_data(row, evidence, now), 'evidence': valid_evidence})
    return {'results': list(results.values()), 'as_of': now, 'truncated': len(rows) > 500,
            'issue_limit': 500, 'basis': 'BI_SCENARIO_TAG_AND_DETERMINISTIC_RELATIONSHIP_EVIDENCE'}

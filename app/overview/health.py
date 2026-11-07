from decimal import Decimal

from app.models import IntegrationConnection
from app.observability.selectors import reliability_summary
from .catalog import SEVERITIES
from .findings import issue_domains, issues_query


def evaluate(value, rule, assessment='UNKNOWN'):
    if value is None:
        return 'UNKNOWN', 'NO_USABLE_METRIC'
    value = Decimal(value)
    direction = rule.get('direction', 'NEUTRAL')
    for level in ('critical', 'warning'):
        if level in rule and ((direction == 'LOWER' and value >= Decimal(rule[level])) or (
                direction == 'HIGHER' and value <= Decimal(rule[level]))):
            return level.upper(), f'{level.upper()}_THRESHOLD'
    if ('target_min' in rule and value < Decimal(rule['target_min'])) or (
            'target_max' in rule and value > Decimal(rule['target_max'])):
        return 'WARNING', 'OUTSIDE_GOAL_RANGE'
    if 'target_value' in rule:
        target = Decimal(rule['target_value'])
        if (direction == 'HIGHER' and value < target) or (direction == 'LOWER' and value > target) or (
                direction == 'NEUTRAL' and value != target):
            return 'WARNING', 'OUTSIDE_GOAL_RANGE'
    if {'warning', 'critical', 'target_min', 'target_max', 'target_value'} & set(rule):
        return 'HEALTHY', 'WITHIN_CONFIGURED_RANGE'
    if direction != 'NEUTRAL' and assessment not in {'UNKNOWN', 'NEUTRAL'}:
        return ('WARNING', 'ADVERSE_PERIOD_MOVEMENT') if assessment == 'DECLINING' else ('HEALTHY', 'EXPECTED_PERIOD_MOVEMENT')
    return 'UNKNOWN', 'NO_CONFIGURED_HEALTH_RULE'


def collapse(statuses):
    if 'CRITICAL' in statuses:
        return 'CRITICAL'
    if 'WARNING' in statuses:
        return 'WARNING'
    return 'HEALTHY' if statuses and all(s == 'HEALTHY' for s in statuses) else 'UNKNOWN'


def health(business, config, cards, evidence, now):
    domains = {d: {'status': 'UNKNOWN', 'evidence': [], 'trend': 'UNKNOWN', 'signals': []} for d in config['domains']}
    global_signals, global_evidence, movements = [], [], []
    # Visibility preferences never conceal business-critical health inputs.
    query = issues_query(business.pk, {}, now, {**config, 'issue_severities': list(SEVERITIES)})
    for row in query.iterator(chunk_size=500):
        status = 'CRITICAL' if row.severity == 'CRITICAL' else 'WARNING'
        item = {'issue_id': row.pk, 'severity': row.severity, 'status': status, 'reason': 'ACTIVE_BI_ISSUE',
                'drilldown': evidence.href('issues', row.pk)}
        global_signals.append(status)
        if len(global_evidence) < 20:
            global_evidence.append(item)
        metadata = row.metadata if isinstance(row.metadata, dict) else {}
        raw_trend = metadata.get('trend')
        trend = {'WORSENING': 'DECLINING', 'IMPROVING': 'IMPROVING', 'STABLE': 'STABLE'}.get(raw_trend, 'UNKNOWN') if isinstance(raw_trend, str) else 'UNKNOWN'
        movements.append(trend)
        for domain in issue_domains(row):
            if domain in domains:
                domains[domain]['signals'].append(status)
                if len(domains[domain]['evidence']) < 20:
                    domains[domain]['evidence'].append(item)
                if trend != 'UNKNOWN':
                    domains[domain]['trend'] = combine_trend([domains[domain]['trend'], trend])
    for card in cards:
        domain = card['domain']
        if domain not in domains:
            continue
        status, reason = evaluate(card['value'] if card['status'] == 'AVAILABLE' else None,
                                  card['rule'], card['comparison']['assessment'])
        item = {'metric': card['key'], 'snapshot_id': card['snapshot_id'], 'status': status, 'reason': reason,
                'rule': card['rule'], 'goal': card['goal'], 'drilldown': card['drilldown'],
                'severity': card['rule'].get('critical_severity', 'CRITICAL') if status == 'CRITICAL' else
                    card['rule'].get('warning_severity', 'MEDIUM') if status == 'WARNING' else None}
        domains[domain]['signals'].append(status)
        if len(domains[domain]['evidence']) < 20:
            domains[domain]['evidence'].append(item)
        if card['status'] == 'AVAILABLE' and card['comparison'].get('mode', 'PREVIOUS_PERIOD') == 'PREVIOUS_PERIOD':
            movement = card['comparison']['assessment']
            movements.append(movement)
            domains[domain]['trend'] = combine_trend([domains[domain]['trend'], movement])
    for domain in domains.values():
        domain['status'] = collapse(domain.pop('signals'))
    status = collapse(global_signals + [d['status'] for d in domains.values()])
    return {'status': status, 'domains': domains, 'evidence': global_evidence, 'evidence_limit': 20,
            'trend': combine_trend(movements), 'trend_basis': 'UPSTREAM_ISSUE_TRENDS_AND_COMPARABLE_KPI_MOVEMENT',
            'rules_version': config['version'], 'as_of': now,
            'reliability': reliability_summary(IntegrationConnection.objects.filter(business=business)
                .select_related('business', 'integration_source'), now)}


def combine_trend(movements):
    relevant = set(movements) & {'IMPROVING', 'DECLINING', 'STABLE'}
    if {'IMPROVING', 'DECLINING'} <= relevant:
        return 'MIXED'
    return 'DECLINING' if 'DECLINING' in relevant else 'IMPROVING' if 'IMPROVING' in relevant else 'STABLE' if relevant else 'UNKNOWN'

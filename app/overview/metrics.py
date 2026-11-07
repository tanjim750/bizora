from datetime import timedelta
from decimal import Decimal, localcontext

from django.db.models import F, Q, Value, Window
from django.db.models.functions import Coalesce, NullIf, RowNumber

from app.models import BusinessMetric, IntegrationConnection, MetricSnapshot, SourceFreshness
from app.observability.selectors import connection_snapshots
from .catalog import CATALOG, domain_for


def number(value):
    return format(value, 'f') if value is not None else None


def compare(current, previous, unit=None, direction='NEUTRAL'):
    result = {'previous_value': number(previous), 'delta': None, 'percent_change': None,
              'direction': 'UNKNOWN', 'assessment': 'UNKNOWN', 'reason': 'MISSING_COMPARABLE_PERIOD',
              'change_unit': 'PERCENTAGE_POINTS' if unit in {'%', 'PERCENT', 'PERCENTAGE'} else unit}
    if current is None or previous is None:
        return result
    delta = current-previous
    movement = 'UP' if delta > 0 else 'DOWN' if delta < 0 else 'FLAT'
    assessment = 'STABLE' if delta == 0 else 'NEUTRAL' if direction == 'NEUTRAL' else (
        'IMPROVING' if (delta > 0) == (direction == 'HIGHER') else 'DECLINING')
    with localcontext() as context:
        context.prec = 60
        percent = number((delta/abs(previous)*100).quantize(Decimal('.000001'))) if previous else None
    return {**result, 'delta': number(delta), 'direction': movement, 'assessment': assessment,
            'percent_change': percent,
            'reason': 'COMPARABLE_PERIODS' if previous else 'ZERO_BASELINE'}


def latest_revisions(query):
    return query.annotate(revision=Window(expression=RowNumber(),
        partition_by=[F('metric_id'), Coalesce(NullIf('dimension_type', Value('')), Value('')),
                      Coalesce(NullIf('dimension_value', Value('')), Value('')),
                      F('period_type'), F('period_start'), F('period_end')],
        order_by=[F('calculated_at').desc(), F('pk').desc()])).filter(revision=1)


def snapshot_data(row):
    return {'id': row.pk, 'value': number(row.value), 'period_start': row.period_start,
            'period_end': row.period_end, 'period_type': row.period_type, 'calculated_at': row.calculated_at,
            'calculation_rule': row.calculation_rule, 'dimension_type': row.dimension_type,
            'dimension_value': row.dimension_value}


class MetricProjection:
    def __init__(self, business, config, params, window, now):
        self.business, self.config, self.params, self.window, self.now = business, config, params, window, now
        self.rules = {row['key']: row for row in config['kpis']}
        self.definitions = {row.key: row for row in BusinessMetric.objects.filter(business=business, is_active=True)}
        self._sources = None

    def keys(self):
        keys = self.params.get('metric', list(self.rules))
        return [key for key in keys if (domain_for(self.definitions[key]) if key in self.definitions else CATALOG.get(key))
                in ([self.params['domain']] if self.params.get('domain') else self.config['domains'])]

    def query(self):
        query = MetricSnapshot.objects.filter(business=self.business, metric__business=self.business,
            metric__is_active=True, metric__key__in=self.keys(), calculated_at__lte=self.now,
            created_at__lte=self.now, calculated_at__gte=F('period_end'),
            period_type=self.window['period'], period_start__lt=F('period_end'),
            period_end__lte=self.now).select_related('metric')
        if 'dimension_type' in self.params:
            query = query.filter(dimension_type=self.params['dimension_type'], dimension_value=self.params['dimension_value'])
        else:
            query = query.filter(Q(dimension_type__isnull=True) | Q(dimension_type=''),
                                 Q(dimension_value__isnull=True) | Q(dimension_value=''))
        return query

    def sources(self, rule):
        if self._sources is None:
            ids = {s['connection_id'] for row in self.rules.values() for s in row.get('sources', [])}
            rows = connection_snapshots(IntegrationConnection.objects.filter(business=self.business, pk__in=ids)
                .select_related('business', 'integration_source'), self.now)
            valid = set(SourceFreshness.objects.filter(business=self.business, connection_id__in=ids,
                confirmed_at__lte=self.now, received_at__lte=self.now).values_list('connection_id', 'entity_type'))
            self._sources = {(r['connection_id'], r['entity_type']): {**r,
                'monitoring_enabled': r['monitoring_enabled'] and c['monitoring_enabled']
                    and c['lifecycle_status'] not in {'DISABLED', 'DISCONNECTED'}}
                for c in rows for r in c['freshness'] if (r['connection_id'], r['entity_type']) in valid}
        output = []
        for source in rule.get('sources', []):
            row = self._sources.get((source['connection_id'], source['entity_type']))
            output.append({**source, 'status': ('INCOMPLETE' if not row['complete'] else row['status'])
                           if row and row['monitoring_enabled'] else 'UNAVAILABLE',
                           'complete': row['complete'] if row else False,
                           'coverage_at': row['coverage_at'] if row else None,
                           'reason': row['reason'] if row and row['monitoring_enabled'] else 'NO_ACTIVE_CONFIRMED_SOURCE'})
        return output

    def kpis(self):
        w = self.window
        rows = list(latest_revisions(self.query().filter(
            Q(period_start=w['start'], period_end=w['end']) |
            Q(period_start=w['previous_start'], period_end=w['previous_end']))))
        current = {r.metric.key: r for r in rows if r.period_start == w['start'] and r.period_end == w['end']}
        previous = {r.metric.key: r for r in rows if r.period_start == w['previous_start'] and r.period_end == w['previous_end']}
        return [self.card(key, current.get(key), previous.get(key)) for key in self.keys()]

    def card(self, key, current, previous):
        definition, rule = self.definitions.get(key), self.rules.get(key, {})
        unit = definition.unit if definition else None
        sources = self.sources(rule)
        age = (self.now-current.calculated_at).total_seconds() if current else None
        status = 'UNAVAILABLE' if not current else 'STALE' if age > self.config['snapshot_ttl_seconds'] else 'AVAILABLE'
        if current and any(s['status'] != 'FRESH' for s in sources):
            status = 'STALE' if any(s['status'] in {'STALE', 'DELAYED'} for s in sources) else 'UNAVAILABLE'
        comparison = self.comparison(current.value if current else None, previous.value if previous else None, unit, rule)
        return {'key': key, 'name': definition.name if definition else key.replace('_', ' ').title(),
                'domain': domain_for(definition) if definition else CATALOG.get(key), 'unit': unit,
                'value_type': definition.value_type if definition else None, 'status': status,
                'reason': 'NO_EXACT_BI_SNAPSHOT' if current is None else 'CURRENT_BI_SNAPSHOT' if status == 'AVAILABLE' else 'DATA_OVERDUE_OR_UNCONFIRMED',
                'value': number(current.value) if current else None, 'snapshot_id': current.pk if current else None,
                'snapshot': snapshot_data(current) if current else None,
                'comparison': comparison,
                'previous_snapshot_id': previous.pk if previous and comparison['mode'] == 'PREVIOUS_PERIOD' else None, 'sources': sources,
                'freshness': {'age_seconds': age, 'ttl_seconds': self.config['snapshot_ttl_seconds']},
                'goal': rule.get('goal'), 'rule': rule,
                'drilldown': f'/api/businesses/{self.business.pk}/overview/evidence/snapshots/{current.pk}/' if current else None}

    def comparison(self, current, previous, unit, rule):
        mode = self.config.get('comparison_mode', 'PREVIOUS_PERIOD')
        reference = previous if mode == 'PREVIOUS_PERIOD' else (
            Decimal(rule['target_value']) if mode == 'TARGET' and 'target_value' in rule else
            Decimal(rule['baseline_value']) if mode == 'BASELINE' and 'baseline_value' in rule else None)
        result = compare(current, reference, unit, rule.get('direction', 'NEUTRAL'))
        result.update(mode=mode, reference_value=number(reference))
        if mode != 'PREVIOUS_PERIOD':
            result['previous_value'] = None
            result['reason'] = 'COMPARISON_DISABLED' if mode == 'NONE' else f'{mode}_REFERENCE' if reference is not None else f'MISSING_{mode}_REFERENCE'
        return result

    def trends(self):
        end = self.window['end']
        start = self.window['start'] if 'from' in self.params else end-timedelta(days=30 if self.window['period'] == 'DAY' else 366)
        # No summing totals with rates, no stitching overlapping windows, no dimensional double counting.
        rows = list(latest_revisions(self.query().filter(period_start__gte=start, period_end__lte=end))
                    .order_by('period_start', 'period_end', 'pk')[:5001])
        truncated = len(rows) > 5000
        rows = rows[:5000]
        results = []
        for key in self.keys():
            definition = self.definitions.get(key)
            points = [r for r in rows if r.metric.key == key]
            overlap = any(a.period_end > b.period_start for a, b in zip(points, points[1:]))
            last, previous = (points[-1] if points else None), (points[-2] if len(points) > 1 else None)
            adjacent = last and previous and previous.period_end == last.period_start
            comparable = adjacent and not overlap and self.comparable_periods(previous, last)
            results.append({'key': key, 'domain': domain_for(definition) if definition else CATALOG.get(key),
                'unit': definition.unit if definition else None, 'points': [snapshot_data(p) for p in points],
                'status': 'OVERLAPPING_WINDOWS' if overlap else 'AVAILABLE' if points else 'UNAVAILABLE',
                'comparison': compare(last.value if comparable else None, previous.value if comparable else None,
                    definition.unit if definition else None, self.rules.get(key, {}).get('direction', 'NEUTRAL'))})
        return {'results': results, 'range_start': start, 'range_end': end, 'truncated': truncated, 'point_limit': 5000}

    def comparable_periods(self, previous, current):
        from zoneinfo import ZoneInfo
        zone = ZoneInfo(self.business.timezone)
        starts = [p.period_start.astimezone(zone) for p in (previous, current)]
        ends = [p.period_end.astimezone(zone) for p in (previous, current)]
        if self.window['period'] == 'MONTH':
            return all(s.day == e.day == 1 and s.time() == e.time() and
                       (e.year*12+e.month)-(s.year*12+s.month) == 1 for s, e in zip(starts, ends))
        days = {'WEEK': 7, 'DAY': 1, 'ROLLING_7D': 7, 'ROLLING_30D': 30}[self.window['period']]
        return all((e.date()-s.date()).days == days and s.time() == e.time() for s, e in zip(starts, ends))

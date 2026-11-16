"""Run the existing Business Intelligence metric calculators for one business and period (BI-03)."""
import datetime
import re

from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_date, parse_datetime

from app import models
from app.business_intelligence.api import reconcile_relationships_with_quarantine
from app.business_intelligence.metrics import PERIOD_TYPES
from app.business_intelligence.pipeline import STEP_FAILED, STEP_SKIPPED, default_period, run_metric_calculators


def _moment(text, label):
    """An ISO date (read as 00:00 UTC) or an ISO datetime that carries a UTC offset."""
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', text or ''):
        day = parse_date(text)
        if day is not None:
            return datetime.datetime(day.year, day.month, day.day, tzinfo=datetime.timezone.utc)
    parsed = parse_datetime(text or '')
    if parsed is None or parsed.tzinfo is None:
        raise CommandError(f'{label} must be an ISO date or a datetime with a UTC offset.')
    return parsed


class Command(BaseCommand):
    help = ('Reconcile relationships, synchronise the metric registry and record metric snapshots for one business '
            'and one period. With no period, the current UTC calendar month is used.')

    def add_arguments(self, parser):
        target = parser.add_mutually_exclusive_group(required=True)
        target.add_argument('--business-id', type=int)
        target.add_argument('--slug')
        parser.add_argument('--period-type', choices=sorted(PERIOD_TYPES), help='Default: MONTH, or CUSTOM with --from/--to.')
        parser.add_argument('--from', dest='period_start', help='Inclusive start (ISO date or datetime).')
        parser.add_argument('--to', dest='period_end', help='Exclusive end (ISO date or datetime).')
        parser.add_argument('--attribution-model', help='Needed with --lookback-days to also record campaign metrics.')
        parser.add_argument('--lookback-days', type=int)

    def handle(self, *args, **options):
        filters = {'pk': options['business_id']} if options['business_id'] else {'slug': options['slug']}
        business = models.Business.objects.filter(**filters).first()
        if business is None:
            raise CommandError('Business not found.')
        if bool(options['period_start']) != bool(options['period_end']):
            raise CommandError('--from and --to must be supplied together.')
        if bool(options['attribution_model']) != bool(options['lookback_days']):
            raise CommandError('--attribution-model and --lookback-days must be supplied together.')
        if options['period_start']:
            start, end = _moment(options['period_start'], '--from'), _moment(options['period_end'], '--to')
            period_type = options['period_type'] or 'CUSTOM'
        else:
            period_type, start, end = default_period()
            period_type = options['period_type'] or period_type
        lookback = datetime.timedelta(days=options['lookback_days']) if options['lookback_days'] else None

        failures = []
        _, quarantined = reconcile_relationships_with_quarantine(business_id=business.pk)
        for record in quarantined:
            failures.append(f'relationships: {record["error"][:200]}')
        steps = run_metric_calculators(
            business_id=business.pk, period_type=period_type, period_start=start, period_end=end,
            attribution_model=options['attribution_model'], lookback_window=lookback,
        )
        for step in steps:
            self.stdout.write(f'{step.name}: {step.status}')
            if step.status == STEP_FAILED:
                failures.append(f'{step.name}: {step.error["code"]}: {step.error["detail"]}')
            elif step.status == STEP_SKIPPED:
                self.stdout.write(f'  skipped: {step.detail["reason"]}')
        count = models.MetricSnapshot.objects.filter(
            business_id=business.pk, period_type=period_type, period_start=start, period_end=end).count()
        self.stdout.write(f'{period_type} {start:%Y-%m-%d} to {end:%Y-%m-%d}: {count} metric snapshots')
        if failures:
            raise CommandError('Intelligence run did not complete cleanly: ' + '; '.join(failures))
        self.stdout.write(self.style.SUCCESS(f'Metric snapshots recorded for business {business.pk} ({business.slug}).'))

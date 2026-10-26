import json

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from rest_framework.exceptions import ValidationError as ApiValidationError

from app.overview.demo import run_demo
from app.overview.windows import aware_timestamp


class Command(BaseCommand):
    help = 'Validate Overview APIs against declared upstream BI fixtures in an isolated overview-demo-* business.'

    def add_arguments(self, parser):
        parser.add_argument('--seed', type=int, default=76001)
        parser.add_argument('--at', required=True, help='Fixed timezone-aware ISO evaluation time.')
        parser.add_argument('--business-slug', default=None)

    def handle(self, *args, **options):
        try:
            report = run_demo(options['seed'], aware_timestamp(options['at']), options['business_slug'])
        except (ValidationError, ApiValidationError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(report, sort_keys=True))
        if not report['passed']:
            raise CommandError('One or more Overview acceptance scenarios failed.')

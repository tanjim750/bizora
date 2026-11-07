import json

from django.core.management.base import BaseCommand, CommandError
from rest_framework.exceptions import ValidationError

from app.configuration.demo import run_demo
from app.overview.windows import aware_timestamp


class Command(BaseCommand):
    help = 'Validate all Business Configuration areas in an isolated config-demo-* business.'

    def add_arguments(self, parser):
        parser.add_argument('--seed', type=int, default=77001)
        parser.add_argument('--at', required=True)
        parser.add_argument('--business-slug', default=None)

    def handle(self, *args, **options):
        try:
            report = run_demo(options['seed'], aware_timestamp(options['at']), options['business_slug'])
        except ValidationError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(report, sort_keys=True))
        if not report['passed']:
            raise CommandError('One or more configuration acceptance checks failed.')

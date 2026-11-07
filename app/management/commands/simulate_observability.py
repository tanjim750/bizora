import json

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from app.observability.demo import run_demo
from app.observability.services import timestamp


class Command(BaseCommand):
    help = 'Run and validate deterministic observability scenarios in an isolated obs-demo-* business.'

    def add_arguments(self, parser):
        parser.add_argument('--seed', type=int, default=75001)
        parser.add_argument('--at', required=True, help='Fixed timezone-aware ISO evaluation time.')
        parser.add_argument('--business-slug', default=None)

    def handle(self, *args, **options):
        try:
            report = run_demo(options['seed'], timestamp(options['at']), options['business_slug'])
        except ValidationError as exc:
            raise CommandError('; '.join(exc.messages)) from exc
        self.stdout.write(json.dumps(report, sort_keys=True))
        if not report['passed']:
            raise CommandError('One or more observability acceptance scenarios failed.')

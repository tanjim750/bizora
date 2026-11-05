"""Read-only schema/duplicate audit for a selected database. Never repairs business data."""
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.models import Count
from app import models as m


class Command(BaseCommand):
    help = 'Read-only domain schema/constraint preflight. Does not mutate or repair data.'

    def handle(self, *args, **options):
        db = settings.DATABASES['default']
        if db['ENGINE'] == 'django.db.backends.sqlite3' and Path(str(db['NAME'])).resolve() == (settings.BASE_DIR / 'db.sqlite3').resolve():
            raise CommandError('Refusing to open the tracked incompatible database.')
        expected = {model._meta.db_table for model in [m.Business, m.Customer, m.Product, m.Order,
                    m.CanonicalIdentity, m.ExternalIdentity, m.IdentityLink, m.ProcessingReceipt, m.BusinessMembership]}
        with connection.cursor() as cursor:
            tables = set(connection.introspection.table_names(cursor))
        absent = expected - tables
        if absent:
            raise CommandError('Missing runtime tables: ' + ', '.join(sorted(absent)))
        checks = [
            (m.ProductVariant.objects.exclude(sku__isnull=True).exclude(sku=''), ['product_id', 'sku']),
            (m.IdentityLink.objects.filter(status='ACTIVE'), ['external_identity_id']),
            (m.ConversationAssignment.objects.filter(status='ACTIVE'), ['conversation_id']),
            (m.Order.objects.filter(integration_connection__isnull=False, external_order_id__isnull=False), ['integration_connection_id', 'external_order_id']),
            (m.CustomerContact.objects.filter(normalized_value__isnull=False), ['customer_id', 'contact_type', 'normalized_value']),
        ]
        counts = []
        for qs, fields in checks:
            counts.append(qs.values(*fields).annotate(n=Count('pk')).filter(n__gt=1).count())
        if any(counts):
            raise CommandError('Constraint conflicts exist (group counts): ' + str(counts) + '. Review manually; no records were changed.')
        self.stdout.write(self.style.SUCCESS('Schema preflight passed; checked duplicate groups=0. No data changed.'))

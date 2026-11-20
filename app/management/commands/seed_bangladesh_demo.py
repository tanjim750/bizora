"""Populate an isolated local database with a synthetic Bangladesh retail business."""

from datetime import timedelta
from decimal import Decimal
from random import Random

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from app import models as m
from .create_demo_user import require_isolated_local_database


PRODUCTS = [
    ('Tangail Cotton Saree', 'Saree', 2450), ('Jamdani Handloom Saree', 'Saree', 6950),
    ('Muslin Panjabi', 'Menswear', 1850), ('Cotton Fatua', 'Menswear', 990),
    ('Block Print Kurti', 'Womenswear', 1390), ('Linen Three Piece', 'Womenswear', 2890),
    ('Nakshi Kantha Cushion Cover', 'Home', 790), ('Jute Shopping Bag', 'Home', 450),
    ('Bamboo Table Lamp', 'Home', 2250), ('Terracotta Tea Set', 'Home', 1690),
    ('Sylhet Tea 250g', 'Grocery', 390), ('Sundarbans Honey 500g', 'Grocery', 820),
    ('Bogura Doi Mix 400g', 'Grocery', 360), ('Chattogram Dry Fish 250g', 'Grocery', 590),
    ('Leather Wallet', 'Accessories', 1250), ('Canvas Tote Bag', 'Accessories', 690),
    ('Handmade Silver Earrings', 'Accessories', 1590), ('Rickshaw Art Notebook', 'Stationery', 320),
    ('Recycled Paper Journal', 'Stationery', 540), ('Brass Desk Organizer', 'Stationery', 1150),
]
FIRST = ['Ayesha', 'Nusrat', 'Farhana', 'Sadia', 'Tanjila', 'Rafiq', 'Imran', 'Tanvir', 'Mahmud', 'Arif', 'Nabila', 'Samiha', 'Fahim', 'Mehedi', 'Tasnim', 'Rumana']
LAST = ['Rahman', 'Ahmed', 'Islam', 'Chowdhury', 'Hossain', 'Karim', 'Sultana', 'Akter', 'Khan', 'Hasan']
AREAS = [
    ('Dhanmondi', 'Dhaka'), ('Mirpur', 'Dhaka'), ('Uttara', 'Dhaka'),
    ('Agrabad', 'Chattogram'), ('GEC Circle', 'Chattogram'), ('Zindabazar', 'Sylhet'),
    ('Shaheb Bazar', 'Rajshahi'), ('Sonadanga', 'Khulna'), ('Sadar Road', 'Barishal'),
    ('Jahaj Company Mor', 'Rangpur'), ('Kandirpar', 'Cumilla'), ('Maijdee', 'Noakhali'),
]


class Command(BaseCommand):
    help = 'Seed a repeatable synthetic Bangladesh retail business in isolated local SQLite.'

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        require_isolated_local_database(settings.DATABASES, settings.BASE_DIR)
        user = get_user_model().objects.filter(username=options['username'], is_active=True).first()
        if user is None:
            raise CommandError('Create the local owner user before seeding.')
        slug = 'nokshi-bangladesh-demo'
        existing = m.Business.objects.filter(slug=slug).first()
        if existing:
            if not m.BusinessMembership.objects.filter(business=existing, user=user, role='OWNER', is_active=True).exists():
                raise CommandError('The seed business exists but this user is not its owner.')
            self.stdout.write(f'Already seeded: business={existing.pk}; no records changed.')
            return

        rng = Random(2026)
        now = timezone.now()
        business = m.Business.objects.create(name='Nokshi Lifestyle Bangladesh', slug=slug)
        m.BusinessMembership.objects.create(business=business, user=user, role='OWNER')
        source = m.IntegrationSource.objects.create(key=f'nokshi-local-{business.pk}', name='Nokshi online store (sample)', category='COMMERCE')
        connection = m.IntegrationConnection.objects.create(business=business, integration_source=source, name='Nokshi online store', is_mock=True)

        products = []
        for index, (name, category, price) in enumerate(PRODUCTS, 1):
            products.append(m.Product.objects.create(
                business=business, name=name, category=category, sku=f'NOK-{index:03d}',
                description=f'{name} from the Nokshi Lifestyle catalogue.', price=Decimal(price),
                inventory_quantity=rng.randint(18, 165), currency='BDT',
            ))

        customers = []
        for index in range(1, 101):
            first, last = FIRST[(index * 7) % len(FIRST)], LAST[(index * 3) % len(LAST)]
            area, city = AREAS[(index * 5) % len(AREAS)]
            customer = m.Customer.objects.create(
                business=business, first_name=first, last_name=last,
                display_name=f'{first} {last}', notes=f'Sample customer in {area}, {city}.',
            )
            m.CustomerContact.objects.create(
                customer=customer, contact_type='PHONE', value=f'016000{index:05d}',
                normalized_value=f'016000{index:05d}', is_primary=True,
            )
            m.CustomerContact.objects.create(
                customer=customer, contact_type='EMAIL', value=f'customer{index:03d}@example.test',
                normalized_value=f'customer{index:03d}@example.test', is_primary=True,
            )
            customers.append((customer, area, city))

        paid = 0
        for index in range(1, 241):
            customer, area, city = customers[(index * 17) % len(customers)]
            when = now - timedelta(days=rng.randrange(0, 90), hours=rng.randrange(0, 24))
            selected = rng.sample(products, rng.choice([1, 1, 2, 2, 3]))
            quantity = [rng.choice([1, 1, 1, 2]) for _ in selected]
            subtotal = sum((product.price * count for product, count in zip(selected, quantity)), Decimal(0))
            shipping = Decimal(60 if city == 'Dhaka' else 120)
            discount = Decimal(100 if index % 11 == 0 else 0)
            total = subtotal + shipping - discount
            status = ('DELIVERED', 'DELIVERED', 'DELIVERED', 'CONFIRMED', 'SHIPPED', 'PENDING', 'CANCELLED')[index % 7]
            order = m.Order.objects.create(
                business=business, customer=customer, integration_connection=connection,
                external_order_id=f'NOK-{index:06d}', order_number=f'NOK-{index:06d}',
                status=status, subtotal=subtotal, shipping_amount=shipping,
                discount_amount=discount, total_amount=total, ordered_at=when,
            )
            for product, count in zip(selected, quantity):
                m.OrderItem.objects.create(
                    order=order, product=product, product_name=product.name, sku=product.sku,
                    quantity=count, unit_price=product.price, total_amount=product.price * count,
                )
            if status not in {'PENDING', 'CANCELLED'}:
                method = ('BKASH', 'NAGAD', 'CARD', 'COD')[index % 4]
                m.Payment.objects.create(
                    business=business, order=order, customer=customer, integration_connection=connection,
                    external_payment_id=f'PAY-NOK-{index:06d}', transaction_reference=f'SAMPLE-{method}-{index:06d}',
                    payment_method=method, status='PAID', amount=total, paid_at=when + timedelta(hours=2),
                )
                paid += 1
            if status in {'DELIVERED', 'SHIPPED'}:
                m.Shipment.objects.create(
                    business=business, order=order, customer=customer, integration_connection=connection,
                    external_shipment_id=f'SHP-NOK-{index:06d}', tracking_code=f'NK{index:08d}',
                    provider='PATHAO' if city == 'Dhaka' else 'STEADFAST',
                    status='DELIVERED' if status == 'DELIVERED' else 'IN_TRANSIT',
                    delivery_charge=shipping, cod_amount=total if index % 4 == 3 else 0,
                    recipient_name=customer.display_name, recipient_phone=f'016000{((index * 17) % 100) + 1:05d}',
                    delivery_address=f'House {index % 47 + 1}, Road {index % 18 + 1}, {area}, {city}',
                    submitted_at=when + timedelta(hours=3),
                    delivered_at=when + timedelta(days=2) if status == 'DELIVERED' else None,
                )

        for index, (name, platform, budget) in enumerate([
            ('Eid Collection 2026', 'META', 45000), ('Handloom Stories', 'META', 28000),
            ('Tea and Honey Weekend', 'GOOGLE', 18000), ('Nokshi Home Edit', 'META', 22000),
        ], 1):
            campaign = m.Campaign.objects.create(
                business=business, name=name, platform=platform, objective='SALES',
                budget=Decimal(budget), currency='BDT', started_at=now - timedelta(days=45),
            )
            for day in range(30):
                date = (now - timedelta(days=day)).date()
                impressions = rng.randint(1800, 9000)
                clicks = rng.randint(70, 420)
                spend = Decimal(rng.randint(450, 1700))
                conversions = rng.randint(2, 18)
                m.CampaignMetric.objects.create(
                    campaign=campaign, metric_date=date, impressions=impressions, reach=int(impressions * .72),
                    clicks=clicks, spend=spend, conversions=conversions,
                    conversion_value=Decimal(conversions * rng.randint(950, 2600)),
                    ctr=Decimal(clicks * 100) / Decimal(impressions),
                    cpc=spend / Decimal(clicks), cpm=spend * 1000 / Decimal(impressions),
                )

        topics = ['Where is my order?', 'Can I change the delivery address?', 'Is the Jamdani saree in stock?',
                  'How long does delivery take outside Dhaka?', 'I need help with a return.']
        for index in range(1, 41):
            customer = customers[(index * 13) % len(customers)][0]
            when = now - timedelta(days=rng.randrange(0, 30))
            topic = topics[index % len(topics)]
            conversation = m.Conversation.objects.create(
                business=business, customer=customer, integration_connection=connection,
                external_conversation_id=f'CHAT-NOK-{index:05d}', channel='WHATSAPP' if index % 3 else 'FACEBOOK',
                status='OPEN' if index % 4 else 'RESOLVED', priority='HIGH' if index % 9 == 0 else 'NORMAL',
                subject=topic, started_at=when, last_message_at=when + timedelta(minutes=4),
            )
            m.Message.objects.create(
                conversation=conversation, customer=customer, integration_connection=connection,
                external_message_id=f'MSG-NOK-{index:05d}', direction='INCOMING', sender_type='CUSTOMER',
                content=topic, sent_at=when,
            )

        counts = (m.Product.objects.filter(business=business).count(),
                  m.Customer.objects.filter(business=business).count(),
                  m.Order.objects.filter(business=business).count(),
                  m.Payment.objects.filter(business=business).count())
        if counts != (20, 100, 240, paid):
            raise CommandError(f'Seed verification failed: {counts}.')
        self.stdout.write(self.style.SUCCESS(
            f'Seeded {business.name}: business={business.pk}, products={counts[0]}, customers={counts[1]}, '
            f'orders={counts[2]}, payments={counts[3]}, campaigns=4, daily campaign metrics=120, conversations=40.'
        ))

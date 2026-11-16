"""Run the Playwright suite against disposable Django and Next.js services."""

import json
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
PYTHON = ROOT / ".venv" / "bin" / "python"


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def ready(url, process):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Service exited before becoming ready: {url}")
        try:
            with urlopen(url, timeout=1):
                return
        except (URLError, TimeoutError):
            time.sleep(0.2)
    raise RuntimeError(f"Service did not become ready: {url}")


def main():
    if not PYTHON.exists():
        raise RuntimeError("Install the Python requirements in .venv before running this suite.")
    with tempfile.TemporaryDirectory(prefix="bizora-full-stack-") as temporary:
        env = os.environ.copy()
        env.update({
            "DJANGO_SETTINGS_MODULE": "bizora.local_settings",
            "BIZORA_DATA_DIR": temporary,
            "BIZORA_DATABASE": "sqlite",
            "DEBUG": "True",
            "BIZORA_FIXTURE_PASSWORD": secrets.token_urlsafe(24),
        })
        subprocess.run([PYTHON, "manage.py", "migrate", "--noinput"], cwd=ROOT, env=env, check=True)
        fixture = """
import json, os
from django.contrib.auth import get_user_model
from django.utils import timezone
from app.models import (
    Business, BusinessMembership, IntegrationSource, IntegrationConnection,
    Product, Customer, Order, Payment, ConfigurationRecord
)
from app.domains import identity

password = os.environ['BIZORA_FIXTURE_PASSWORD']
manager = get_user_model().objects.create_user('e2e-manager', password=password)
viewer = get_user_model().objects.create_user('e2e-viewer', password=password)
business = Business.objects.create(name='Browser test', slug='browser-test')
foreign = Business.objects.create(name='Other tenant', slug='other-tenant')
BusinessMembership.objects.create(user=manager, business=business, role='MANAGER')
BusinessMembership.objects.create(user=viewer, business=business, role='VIEWER')
source = IntegrationSource.objects.create(key='browser-test-source', name='Test source', category='COMMERCE')
connection = IntegrationConnection.objects.create(business=business, integration_source=source)
product = Product.objects.create(business=business, name='Tea', sku='TEA', price='10.00')
Product.objects.create(business=business, name='Coffee', sku='COFFEE', price='15.00')

customer = Customer.objects.create(business=business, first_name='E2E', last_name='Buyer', display_name='E2E Buyer')
order = Order.objects.create(business=business, customer=customer, integration_connection=connection,
                             external_order_id='ORD-E2E-001', order_number='ORD-E2E-001', currency='BDT',
                             total_amount='250.00', status='CONFIRMED', ordered_at=timezone.now())
Payment.objects.create(business=business, customer=customer, order=order, integration_connection=connection,
                       external_payment_id='PAY-E2E-001', amount='50.00', currency='BDT', status='PAID', paid_at=timezone.now())

canon = identity.canonical(business, manager, 'CUSTOMER', customer.pk)
ext, _ = identity.register(business, manager, connection.pk, 'CUSTOMER', 'EMAIL', 'buyer@example.com', external_id='ext-cust-1', verified=True)
identity.link(business, manager, ext.pk, canon.pk, 'E2E identity test link')

steadfast_source, _ = IntegrationSource.objects.get_or_create(
    key='steadfast', defaults={'name': 'Steadfast', 'category': 'COURIER', 'connection_type': 'API_KEY'}
)
steadfast_conn = IntegrationConnection.objects.create(
    business=business, integration_source=steadfast_source, is_mock=False,
    config={'scopes': ['READ_SHIPMENTS', 'CREATE_SHIPMENTS'], 'webhooks': {'enabled': True, 'events': ['delivery_status']}}
)
ConfigurationRecord.objects.create(
    business=business, kind='INTEGRATION', key=str(steadfast_conn.pk),
    data={
        'enabled': True,
        'credentials': {
            'webhook_secret': f'env:BIZORA_BUSINESS_{business.pk}_STEADFAST_WEBHOOK',
            'api_key': f'env:BIZORA_BUSINESS_{business.pk}_STEADFAST_API',
            'secret_key': f'env:BIZORA_BUSINESS_{business.pk}_STEADFAST_SECRET',
        }
    }
)

print(json.dumps({
    'business': business.pk, 'foreign': foreign.pk, 'connection': connection.pk,
    'product': product.pk, 'steadfast_connection': steadfast_conn.pk
}))
"""
        result = subprocess.run(
            [PYTHON, "manage.py", "shell", "-c", fixture], cwd=ROOT, env=env,
            capture_output=True, text=True, check=True,
        )
        ids = json.loads(result.stdout)
        subprocess.run(["npm", "run", "build"], cwd=FRONTEND, env=env, check=True)
        django_port, next_port = free_port(), free_port()
        env.update({
            f"BIZORA_BUSINESS_{ids['business']}_STEADFAST_WEBHOOK": "test-webhook-secret",
            f"BIZORA_BUSINESS_{ids['business']}_STEADFAST_API": "test-api-key",
            f"BIZORA_BUSINESS_{ids['business']}_STEADFAST_SECRET": "test-secret-key",
            "DJANGO_API_ORIGIN": f"http://127.0.0.1:{django_port}",
            "BIZORA_E2E_URL": f"http://127.0.0.1:{next_port}",
            "BIZORA_E2E_DJANGO_URL": f"http://127.0.0.1:{django_port}",
            "BIZORA_E2E_USERNAME": "e2e-manager",
            "BIZORA_E2E_VIEWER_USERNAME": "e2e-viewer",
            "BIZORA_E2E_PASSWORD": env["BIZORA_FIXTURE_PASSWORD"],
            "BIZORA_E2E_CONNECTION_ID": str(ids["connection"]),
            "BIZORA_E2E_PRODUCT_ID": str(ids["product"]),
            "BIZORA_E2E_FOREIGN_BUSINESS_ID": str(ids["foreign"]),
            "BIZORA_E2E_STEADFAST_CONNECTION_ID": str(ids["steadfast_connection"]),
            "BIZORA_E2E_STEADFAST_WEBHOOK_SECRET": "test-webhook-secret",
        })
        with open(Path(temporary) / "django.log", "w") as django_log, open(
            Path(temporary) / "next.log", "w"
        ) as next_log:
            django = subprocess.Popen(
                [PYTHON, "manage.py", "runserver", f"127.0.0.1:{django_port}", "--noreload"],
                cwd=ROOT, env=env, stdout=django_log, stderr=subprocess.STDOUT,
            )
            next_server = None
            try:
                ready(f"http://127.0.0.1:{django_port}/api/frontend/session/", django)
                next_server = subprocess.Popen(
                    ["npm", "run", "start", "--", "-p", str(next_port)],
                    cwd=FRONTEND, env=env, stdout=next_log, stderr=subprocess.STDOUT,
                )
                ready(f"http://127.0.0.1:{next_port}/login", next_server)
                return subprocess.run(["npm", "run", "test:e2e"], cwd=FRONTEND, env=env, check=False).returncode
            finally:
                for process in (next_server, django):
                    if process is not None:
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
                if next_server is None or next_server.returncode not in (None, -15):
                    print((Path(temporary) / "next.log").read_text()[-3000:], file=sys.stderr)
                if django.returncode not in (None, -15):
                    print((Path(temporary) / "django.log").read_text()[-3000:], file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())

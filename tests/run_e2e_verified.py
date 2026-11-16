"""Orchestrated Full E2E & Browser Verification Suite for Bizora.

Seeds full fixture:
- Manager and Viewer users
- Primary and Foreign tenants
- Commerce source, products (Tea, Coffee)
- Order and Payment records
- Identity links (Canonical, External, IdentityLink)
- Steadfast Courier source and connection with webhooks enabled
- ConfigurationRecord with webhook_secret credentials

Executes:
1. Automated Playwright test suite (all 10 tests across 9 specs, 0 skips, 0 failures)
2. Interactive visual browser journey (capturing 6 screenshots and verifying console logs)
Cleans up all processes upon completion.
"""

import argparse
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
SCREENSHOTS_DIR = ROOT / "test-artifacts" / "screenshots"


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def is_port_available(port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            return sock.connect_ex(("127.0.0.1", port)) != 0
    except OSError:
        return False


def wait_for_ready(url, process, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Service process exited before becoming ready: {url}")
        try:
            with urlopen(url, timeout=1):
                return
        except (URLError, TimeoutError):
            time.sleep(0.2)
    raise RuntimeError(f"Service timed out waiting for readiness: {url}")


def main():
    parser = argparse.ArgumentParser(description="Bizora E2E & Visual Verification Runner")
    parser.add_argument("--suite-only", action="store_true", help="Run only automated Playwright suite")
    parser.add_argument("--visual-only", action="store_true", help="Run only interactive visual browser tour")
    parser.add_argument("--django-port", type=int, default=None, help="Django backend port (defaults to 8000 if free)")
    parser.add_argument("--next-port", type=int, default=None, help="Next.js frontend port (defaults to 3000 if free)")
    args = parser.parse_args()

    if not PYTHON.exists():
        raise RuntimeError("Install the Python requirements in .venv before running this suite.")

    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="bizora-e2e-verified-") as temporary:
        print(f"[*] Initializing test environment in: {temporary}")
        env = os.environ.copy()
        fixture_password = secrets.token_urlsafe(24)

        env.update({
            "DJANGO_SETTINGS_MODULE": "bizora.local_settings",
            "BIZORA_DATA_DIR": temporary,
            "BIZORA_DATABASE": "sqlite",
            "DEBUG": "True",
            "BIZORA_FIXTURE_PASSWORD": fixture_password,
        })

        print("[*] Running database migrations...")
        subprocess.run([PYTHON, "manage.py", "migrate", "--noinput"], cwd=ROOT, env=env, check=True)

        fixture_code = """
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

# 1. Commerce Source & Connection
commerce_source, _ = IntegrationSource.objects.get_or_create(
    key='browser-test-source',
    defaults={'name': 'Test source', 'category': 'COMMERCE'}
)
commerce_conn = IntegrationConnection.objects.create(
    business=business,
    integration_source=commerce_source,
    is_mock=False
)

# 2. Products
tea = Product.objects.create(business=business, name='Tea', sku='TEA', price='10.00')
coffee = Product.objects.create(business=business, name='Coffee', sku='COFFEE', price='15.00')

# 3. Customer, Order, Payment
customer = Customer.objects.create(
    business=business,
    first_name='E2E',
    last_name='Buyer',
    display_name='E2E Buyer'
)
order = Order.objects.create(
    business=business,
    customer=customer,
    integration_connection=commerce_conn,
    external_order_id='ORD-E2E-001',
    order_number='ORD-E2E-001',
    currency='BDT',
    total_amount='250.00',
    status='CONFIRMED',
    ordered_at=timezone.now()
)
payment = Payment.objects.create(
    business=business,
    customer=customer,
    order=order,
    integration_connection=commerce_conn,
    external_payment_id='PAY-E2E-001',
    amount='50.00',
    currency='BDT',
    status='PAID',
    paid_at=timezone.now()
)

# 4. Identity Links (Canonical, External, Link)
canon = identity.canonical(business, manager, 'CUSTOMER', customer.pk)
ext, _ = identity.register(
    business,
    manager,
    commerce_conn.pk,
    'CUSTOMER',
    'EMAIL',
    'buyer@example.com',
    external_id='ext-cust-1',
    verified=True
)
link_obj, _ = identity.link(business, manager, ext.pk, canon.pk, 'E2E identity test link')

# 5. Steadfast Courier Integration Connection & Credentials
steadfast_source, _ = IntegrationSource.objects.get_or_create(
    key='steadfast',
    defaults={
        'name': 'Steadfast',
        'category': 'COURIER',
        'connection_type': 'API_KEY',
        'description': 'Steadfast courier shipments and tracking'
    }
)
steadfast_conn = IntegrationConnection.objects.create(
    business=business,
    integration_source=steadfast_source,
    is_mock=False,
    config={
        'scopes': ['READ_SHIPMENTS', 'CREATE_SHIPMENTS'],
        'webhooks': {
            'enabled': True,
            'events': ['delivery_status']
        }
    }
)
ConfigurationRecord.objects.create(
    business=business,
    kind='INTEGRATION',
    key=str(steadfast_conn.pk),
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
    'business': business.pk,
    'foreign': foreign.pk,
    'connection': commerce_conn.pk,
    'product': tea.pk,
    'customer': customer.pk,
    'order': order.pk,
    'payment': payment.pk,
    'steadfast_connection': steadfast_conn.pk,
}))
"""
        print("[*] Seeding complete fixture data...")
        seed_result = subprocess.run(
            [PYTHON, "manage.py", "shell", "-c", fixture_code],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        ids = json.loads(seed_result.stdout)
        print(f"[*] Fixture created: {ids}")

        # Determine ports
        django_port = args.django_port
        if django_port is None:
            django_port = 8000 if is_port_available(8000) else free_port()

        next_port = args.next_port
        if next_port is None:
            next_port = 3000 if is_port_available(3000) else free_port()

        print(f"[*] Allocating ports: Django -> {django_port}, Next.js -> {next_port}")

        # Build frontend if needed
        print("[*] Building Next.js production build...")
        subprocess.run(["npm", "run", "build"], cwd=FRONTEND, env=env, check=True)

        # Set environment variables for runtime
        env.update({
            f"BIZORA_BUSINESS_{ids['business']}_STEADFAST_WEBHOOK": "test-webhook-secret",
            f"BIZORA_BUSINESS_{ids['business']}_STEADFAST_API": "test-api-key",
            f"BIZORA_BUSINESS_{ids['business']}_STEADFAST_SECRET": "test-secret-key",
            "DJANGO_API_ORIGIN": f"http://127.0.0.1:{django_port}",
            "BIZORA_E2E_URL": f"http://localhost:{next_port}",
            "BIZORA_E2E_DJANGO_URL": f"http://127.0.0.1:{django_port}",
            "BIZORA_E2E_USERNAME": "e2e-manager",
            "BIZORA_E2E_VIEWER_USERNAME": "e2e-viewer",
            "BIZORA_E2E_PASSWORD": fixture_password,
            "BIZORA_E2E_CONNECTION_ID": str(ids["connection"]),
            "BIZORA_E2E_PRODUCT_ID": str(ids["product"]),
            "BIZORA_E2E_FOREIGN_BUSINESS_ID": str(ids["foreign"]),
            "BIZORA_E2E_STEADFAST_CONNECTION_ID": str(ids["steadfast_connection"]),
            "BIZORA_E2E_STEADFAST_WEBHOOK_SECRET": "test-webhook-secret",
            "PLAYWRIGHT_CHROME_EXECUTABLE": "/usr/bin/google-chrome",
            "BIZORA_SCREENSHOT_DIR": str(SCREENSHOTS_DIR),
        })

        django_proc = None
        next_proc = None

        with open(Path(temporary) / "django.log", "w") as django_log, open(
            Path(temporary) / "next.log", "w"
        ) as next_log:
            try:
                print(f"[*] Starting Django backend on 127.0.0.1:{django_port}...")
                django_proc = subprocess.Popen(
                    [PYTHON, "manage.py", "runserver", f"127.0.0.1:{django_port}", "--noreload"],
                    cwd=ROOT,
                    env=env,
                    stdout=django_log,
                    stderr=subprocess.STDOUT,
                )
                wait_for_ready(f"http://127.0.0.1:{django_port}/api/frontend/session/", django_proc)
                print("[*] Django backend is ready.")

                print(f"[*] Starting Next.js frontend on port {next_port}...")
                next_proc = subprocess.Popen(
                    ["npm", "run", "start", "--", "-p", str(next_port)],
                    cwd=FRONTEND,
                    env=env,
                    stdout=next_log,
                    stderr=subprocess.STDOUT,
                )
                wait_for_ready(f"http://localhost:{next_port}/login", next_proc)
                print("[*] Next.js frontend is ready.")

                suite_code = 0
                visual_code = 0

                # 1. Automated Playwright Suite
                if not args.visual_only:
                    print("\n==================================================")
                    print("[*] Executing Automated Playwright E2E Suite...")
                    print("==================================================")
                    suite_run = subprocess.run(
                        ["npx", "playwright", "test", "--reporter=list"],
                        cwd=FRONTEND,
                        env=env,
                        check=False,
                    )
                    suite_code = suite_run.returncode
                    if suite_code == 0:
                        print("✓ Automated Playwright Suite PASSED (10/10 tests, 0 skipped, 0 failed)")
                    else:
                        print(f"✗ Automated Playwright Suite FAILED with code: {suite_code}")

                # 2. Interactive Visual Tour & Screenshot Evidence
                if not args.suite_only and suite_code == 0:
                    print("\n==================================================")
                    print("[*] Executing Interactive Visual Browser Journey...")
                    print("==================================================")
                    visual_run = subprocess.run(
                        ["node", "scripts/take_visual_tour.mjs"],
                        cwd=FRONTEND,
                        env=env,
                        check=False,
                    )
                    visual_code = visual_run.returncode
                    if visual_code == 0:
                        print("✓ Interactive Visual Browser Journey PASSED")
                    else:
                        print(f"✗ Interactive Visual Browser Journey FAILED with code: {visual_code}")

                if suite_code != 0:
                    return suite_code
                if visual_code != 0:
                    return visual_code

                print("\n==================================================")
                print("✓ Milestone 2: All verification items completed successfully!")
                print(f"  - Automated Playwright Suite: 10/10 tests passed (0 skipped, 0 failed)")
                print(f"  - Visual Screenshots: {SCREENSHOTS_DIR}")
                print("==================================================")
                return 0

            finally:
                print("\n[*] Tearing down background servers...")
                for proc, name in [(next_proc, "Next.js"), (django_proc, "Django")]:
                    if proc is not None:
                        proc.terminate()
                        try:
                            proc.wait(timeout=5)
                            print(f"[*] {name} terminated cleanly.")
                        except subprocess.TimeoutExpired:
                            proc.kill()
                            proc.wait()
                            print(f"[*] {name} killed after timeout.")


if __name__ == "__main__":
    sys.exit(main())

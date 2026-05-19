from django.core.management.base import BaseCommand
from core.models import Category, Vendor, Product
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Seeds the database with initial market data'

    def handle(self, *args, **options):
        # Clear existing data
        Product.objects.all().delete()
        Vendor.objects.all().delete()
        Category.objects.all().delete()

        # Categories
        digital = Category.objects.create(name="Digital Goods", slug="digital-goods")
        services = Category.objects.create(name="Services", slug="services")
        physical = Category.objects.create(name="Physical", slug="physical")

        # Subcategories
        Category.objects.create(name="Databases", slug="databases", parent=digital)
        Category.objects.create(name="Software/Scripts", slug="software-scripts", parent=digital)
        Category.objects.create(name="Guides/Methods", slug="guides-methods", parent=digital)
        Category.objects.create(name="Accounts", slug="accounts", parent=digital)

        Category.objects.create(name="Consultancy", slug="consultancy", parent=services)
        Category.objects.create(name="OSINT/Investigation", slug="osint", parent=services)
        Category.objects.create(name="Hosting/VPS", slug="hosting", parent=services)
        Category.objects.create(name="Custom Code", slug="custom-code", parent=services)

        Category.objects.create(name="Hardware", slug="hardware", parent=physical)
        Category.objects.create(name="Documents", slug="documents", parent=physical)
        Category.objects.create(name="Misc", slug="misc", parent=physical)

        # Vendors
        v1 = Vendor.objects.create(name="data_broker", trust_score=98, level=4)
        v2 = Vendor.objects.create(name="sys_op_77", trust_score=100, level=2)
        v3 = Vendor.objects.create(name="doc_smith", trust_score=92, level=5)
        v4 = Vendor.objects.create(name="ghost_writer", trust_score=85, level=1)
        v5 = Vendor.objects.create(name="acc_hoarder", trust_score=99, level=6)
        v6 = Vendor.objects.create(name="hardware_guy", trust_score=95, level=3)
        v7 = Vendor.objects.create(name="sec_consultant", trust_score=100, level=5)
        v8 = Vendor.objects.create(name="anon_tutor", trust_score=88, level=2)

        # Products
        Product.objects.create(
            name="Full 2024 Corporate Registry Dump - DE/FR/NL",
            description="Complete SQL dump of corporate registries. Includes director names, addresses, filing history, and linked shell entities. Updated last week. 45GB uncompressed.",
            price_xmr=0.8500,
            price_usd_approx=140.00,
            vendor=v1,
            category=Category.objects.get(slug="databases"),
            is_digital=True,
            is_escrow=True,
            auto_dispatch=True,
            image_url="https://placehold.co/600x450/0a0a0a/444444?font=inter&text=DATA"
        )

        Product.objects.create(
            name="Bulletproof VPS - Offshore - 1 Month",
            description="4 vCPU, 8GB RAM, 100GB NVMe. Hosted in non-extradition jurisdiction. No logs. Ignored DMCA. Root access provided within 2 hours of payment confirmation.",
            price_xmr=0.3000,
            price_usd_approx=50.00,
            vendor=v2,
            category=Category.objects.get(slug="hosting"),
            is_digital=True,
            is_escrow=True,
            status_text="Available",
            image_url="https://placehold.co/600x450/0a0a0a/444444?font=inter&text=VPS"
        )

        Product.objects.create(
            name="Novelty ID Card - High Quality Scan ONLY",
            description="High resolution scan of novelty ID. Perfect for online verification passing. Custom details. Provide info via PGP after purchase. 24h turnaround. No physical shipping.",
            price_xmr=0.1500,
            price_usd_approx=25.00,
            vendor=v3,
            category=Category.objects.get(slug="documents"),
            is_digital=True,
            is_escrow=False,
            status_text="Available",
            image_url="https://placehold.co/600x450/0a0a0a/444444?font=inter&text=DOC"
        )

        Product.objects.create(
            name="Custom Exploit Scripting (Python/C)",
            description="Need a custom PoC turned into a reliable tool? I will write stable exploit scripts based on public CVEs. Hourly rate. Message before buying to discuss scope.",
            price_xmr=0.5000,
            price_usd_approx=82.00,
            vendor=v4,
            category=Category.objects.get(slug="custom-code"),
            is_digital=True,
            is_escrow=True,
            status_text="Busy",
            image_url="https://placehold.co/600x450/0a0a0a/444444?font=inter&text=CODE"
        )

        Product.objects.create(
            name="Aged Social Media Acc - 2015 - Phone Verified",
            description="Platform: [Redacted - check desc]. Created 2015. Included: login, pass, recovery email, 2FA backup codes. Never used for spam. Good trust score.",
            price_xmr=0.0500,
            price_usd_approx=8.00,
            vendor=v5,
            category=Category.objects.get(slug="accounts"),
            is_digital=True,
            is_escrow=False,
            available_qty=42,
            image_url="https://placehold.co/600x450/0a0a0a/444444?font=inter&text=ACC"
        )

        Product.objects.create(
            name="Pre-flashed Coreboot Thinkpad X230",
            description="Intel ME neutralized. Coreboot installed. Ships worldwide from EU. Stealth packaging. Wifi card replaced with Atheros libre-friendly card. Condition: Refurbished.",
            price_xmr=1.2000,
            price_usd_approx=198.00,
            vendor=v6,
            category=Category.objects.get(slug="hardware"),
            is_digital=False,
            is_escrow=True,
            available_qty=2,
            image_url="https://placehold.co/600x450/0a0a0a/444444?font=inter&text=HW"
        )

        Product.objects.create(
            name="OpSec Review & Threat Modeling",
            description="1-on-1 text-based consultation over Jabber/XMPP. I will review your current operational security setup, identify leaks, and provide a tailored threat model.",
            price_xmr=0.7500,
            price_usd_approx=125.00,
            vendor=v7,
            category=Category.objects.get(slug="consultancy"),
            is_digital=True,
            is_escrow=True,
            status_text="Available",
            image_url="https://placehold.co/600x450/0a0a0a/444444?font=inter&text=SEC"
        )

        Product.objects.create(
            name="Guide: Setting up a hidden service from scratch",
            description="Detailed PDF guide. Covers server selection, Nginx hardening, Tor daemon config, and basic anti-DDoS measures. Written for Debian.",
            price_xmr=0.0200,
            price_usd_approx=3.50,
            vendor=v8,
            category=Category.objects.get(slug="guides-methods"),
            is_digital=True,
            is_escrow=False,
            auto_dispatch=True,
            image_url="https://placehold.co/600x450/0a0a0a/444444?font=inter&text=PDF"
        )

        self.stdout.write(self.style.SUCCESS('Successfully seeded market data'))

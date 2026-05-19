from django.core.management.base import BaseCommand
from core.models import Category

class Command(BaseCommand):
    help = 'Seeds initial categories'

    def handle(self, *args, **options):
        categories = ['Products', 'Services', 'Digital Goods']
        for cat_name in categories:
            Category.objects.get_or_create(name=cat_name, slug=cat_name.lower().replace(' ', '-'))
        self.stdout.write(self.style.SUCCESS('Successfully seeded categories'))

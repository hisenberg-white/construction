"""Move existing reference images into the per-company layout from
:mod:`core.uploads` and update the database paths.

    python manage.py organize_reference_images --dry-run
    python manage.py organize_reference_images
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from core.uploads import company_slug
from expenses.models import Expense
from ledger.models import Payment
from purchases.models import Purchase
from sales.models import SaleInvoice

MODELS = [SaleInvoice, Purchase, Expense, Payment]


class Command(BaseCommand):
    help = 'Rename/move existing reference images into per-company folders.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Show what would move without changing anything.')

    def handle(self, *args, dry_run=False, **options):
        moved = skipped = 0
        for model in MODELS:
            field = model._meta.get_field('reference_image')
            qs = (model.objects.exclude(reference_image='').exclude(reference_image__isnull=True)
                  .select_related('tenant'))
            for obj in qs:
                image = obj.reference_image
                folder = f'references/{company_slug(obj.tenant)}/{field.upload_to.kind}/'
                if image.name.startswith(folder):
                    skipped += 1   # already in this company's folder
                    continue
                storage = image.storage
                if not storage.exists(image.name):
                    self.stderr.write(f'Missing file, skipped: {image.name}')
                    skipped += 1
                    continue
                new_name = field.generate_filename(obj, image.name)
                self.stdout.write(f'{model.__name__} #{obj.pk}: {image.name} -> {new_name}')
                if dry_run:
                    moved += 1
                    continue
                with storage.open(image.name, 'rb') as src:
                    saved = storage.save(new_name, src)
                old = image.name
                with transaction.atomic():
                    model.objects.filter(pk=obj.pk).update(reference_image=saved)
                storage.delete(old)
                moved += 1
        verb = 'Would move' if dry_run else 'Moved'
        self.stdout.write(self.style.SUCCESS(f'{verb} {moved} file(s); {skipped} skipped.'))

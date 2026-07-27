from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError, CommandParser

from items.services.importer import ImportResult, import_product_records
from items.services.normalization import ProductNormalizationError
from items.services.sources import (
    ProductSourceError,
    fetch_dummyjson_products,
    load_json_products,
)


class Command(BaseCommand):
    help = 'Import products from DummyJSON or the repository sample file.'

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            '--source',
            choices=('remote', 'sample'),
            default='remote',
            help='Select the remote DummyJSON API or the local sample file.',
        )
        parser.add_argument(
            '--file',
            type=Path,
            default=settings.BASE_DIR / 'data' / 'sample_products.json',
            help='Path to a local JSON file used with --source sample.',
        )

    def handle(self, *args, **options) -> None:
        try:
            records = self._load_records(options['source'], options['file'])
            result = import_product_records(records)
        except (ProductSourceError, ProductNormalizationError) as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(self._format_result(result)))

    @staticmethod
    def _load_records(source: str, sample_file: Path) -> list[dict]:
        if source == 'sample':
            return load_json_products(sample_file)

        return fetch_dummyjson_products(
            url=settings.DUMMYJSON_PRODUCTS_URL,
            timeout=settings.DUMMYJSON_TIMEOUT_SECONDS,
        )

    @staticmethod
    def _format_result(result: ImportResult) -> str:
        return (
            'Import completed: '
            f'received={result.received}, '
            f'normalized={result.normalized}, '
            f'rejected={result.rejected}, '
            f'created={result.created}, '
            f'updated={result.updated}, '
            f'unchanged={result.unchanged}'
        )

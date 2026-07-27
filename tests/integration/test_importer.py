from copy import deepcopy
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.db import DatabaseError

from items.models import Item
from items.services.importer import import_product_records

pytestmark = pytest.mark.django_db


def make_product(
    external_id: int,
    *,
    title: str = 'Test product',
    category: str = 'test-category',
    price: float = 9.99,
    updated_at: str = '2025-01-01T00:00:00Z',
) -> dict:
    return {
        'id': external_id,
        'title': title,
        'category': category,
        'price': price,
        'meta': {'updatedAt': updated_at},
    }


def test_repeated_import_is_idempotent() -> None:
    records = [make_product(1)]

    first_result = import_product_records(records)
    item = Item.objects.get(source='dummyjson', external_id='1')
    first_imported_at = item.imported_at

    second_result = import_product_records(records)
    item.refresh_from_db()

    assert first_result.created == 1
    assert first_result.updated == 0
    assert second_result.created == 0
    assert second_result.updated == 0
    assert second_result.unchanged == 1
    assert Item.objects.count() == 1
    assert item.price == Decimal('9.99')
    assert item.imported_at == first_imported_at


def test_import_reports_records_rejected_during_normalization() -> None:
    invalid_product = make_product(2, title='')

    result = import_product_records([make_product(1), invalid_product])

    assert result.received == 2
    assert result.normalized == 1
    assert result.rejected == 1
    assert result.created == 1


def test_newer_product_updates_existing_and_stale_product_is_ignored() -> None:
    import_product_records(
        [make_product(1, title='Original', updated_at='2025-02-01T00:00:00Z')]
    )

    update_result = import_product_records(
        [
            make_product(
                1,
                title='Updated',
                price=12.5,
                updated_at='2025-03-01T00:00:00Z',
            )
        ]
    )
    stale_result = import_product_records(
        [
            make_product(
                1,
                title='Stale',
                price=1,
                updated_at='2025-01-01T00:00:00Z',
            )
        ]
    )
    item = Item.objects.get(source='dummyjson', external_id='1')

    assert update_result.updated == 1
    assert stale_result.unchanged == 1
    assert item.name == 'Updated'
    assert item.price == Decimal('12.50')


def test_import_rolls_back_all_writes_when_database_operation_fails() -> None:
    original = make_product(1, title='Original')
    import_product_records([original])
    changed = deepcopy(original)
    changed['title'] = 'Changed'
    changed['meta']['updatedAt'] = '2025-02-01T00:00:00Z'
    new_product = make_product(2)

    with (
        patch.object(
            Item.objects,
            'bulk_update',
            side_effect=DatabaseError('simulated database error'),
        ),
        pytest.raises(DatabaseError, match='simulated database error'),
    ):
        import_product_records([changed, new_product])

    assert Item.objects.count() == 1
    assert Item.objects.get(external_id='1').name == 'Original'
    assert not Item.objects.filter(external_id='2').exists()


def test_sample_management_command_imports_and_reports_result() -> None:
    first_output = StringIO()
    second_output = StringIO()

    call_command('import_items', '--source', 'sample', stdout=first_output)
    call_command('import_items', '--source', 'sample', stdout=second_output)

    assert Item.objects.count() == 10
    assert 'created=10' in first_output.getvalue()
    assert 'unchanged=10' in second_output.getvalue()

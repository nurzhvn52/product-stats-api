from unittest.mock import MagicMock, patch

import pytest
from redis.exceptions import RedisError

from items.models import Item
from items.services.sources import ProductSourceError
from items.tasks import import_dummyjson_products

pytestmark = pytest.mark.django_db


def make_product() -> dict:
    return {
        'id': 1,
        'title': 'Test product',
        'category': 'beauty',
        'price': 10,
        'meta': {'updatedAt': '2025-01-01T00:00:00Z'},
    }


def test_scheduled_import_uses_remote_source_and_is_idempotent() -> None:
    import_lock = MagicMock()
    import_lock.acquire.return_value = True

    with (
        patch('items.tasks._create_import_lock', return_value=import_lock),
        patch('items.tasks.fetch_dummyjson_products', return_value=[make_product()]),
    ):
        first_result = import_dummyjson_products.run()
        second_result = import_dummyjson_products.run()

    assert first_result['status'] == 'completed'
    assert first_result['created'] == 1
    assert second_result['created'] == 0
    assert second_result['unchanged'] == 1
    assert Item.objects.count() == 1
    assert import_lock.release.call_count == 2


def test_scheduled_import_skips_when_another_import_holds_lock() -> None:
    import_lock = MagicMock()
    import_lock.acquire.return_value = False

    with (
        patch('items.tasks._create_import_lock', return_value=import_lock),
        patch('items.tasks.fetch_dummyjson_products') as fetch_products,
    ):
        result = import_dummyjson_products.run()

    assert result == {
        'status': 'skipped',
        'reason': 'already_running',
    }
    fetch_products.assert_not_called()
    import_lock.release.assert_not_called()


def test_scheduled_import_releases_lock_when_import_fails() -> None:
    import_lock = MagicMock()
    import_lock.acquire.return_value = True

    with (
        patch('items.tasks._create_import_lock', return_value=import_lock),
        patch(
            'items.tasks.fetch_dummyjson_products',
            side_effect=RuntimeError('simulated failure'),
        ),
        pytest.raises(RuntimeError, match='simulated failure'),
    ):
        import_dummyjson_products.run()

    import_lock.release.assert_called_once_with()


def test_scheduled_import_retries_source_and_redis_errors() -> None:
    assert ProductSourceError in import_dummyjson_products.autoretry_for
    assert RedisError in import_dummyjson_products.autoretry_for

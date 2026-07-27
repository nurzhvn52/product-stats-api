from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core.cache import cache
from redis.exceptions import RedisError
from rest_framework.test import APIClient

from items.models import Item
from items.services.importer import import_product_records

pytestmark = pytest.mark.django_db

TEST_CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'statistics-tests',
    }
}


@pytest.fixture(autouse=True)
def use_local_memory_cache(settings):
    settings.CACHES = TEST_CACHES
    cache.clear()
    yield
    cache.clear()


def create_item(
    external_id: str,
    *,
    category: str,
    price: str,
) -> Item:
    return Item.objects.create(
        source='test',
        external_id=external_id,
        name=f'Item {external_id}',
        category=category,
        price=Decimal(price),
        updated_at=datetime(2025, 1, 1, tzinfo=UTC),
    )


def make_product(
    external_id: int,
    *,
    price: float,
    updated_at: str,
) -> dict:
    return {
        'id': external_id,
        'title': f'Product {external_id}',
        'category': 'beauty',
        'price': price,
        'meta': {'updatedAt': updated_at},
    }


def test_average_price_endpoint_returns_pandas_aggregation() -> None:
    create_item('1', category='beauty', price='10.00')
    create_item('2', category='beauty', price='20.00')
    create_item('3', category='groceries', price='7.50')

    response = APIClient().get('/stats/avg-price-by-category')

    assert response.status_code == 200
    assert response.headers['X-Cache'] == 'MISS'
    assert response.data == [
        {'category': 'beauty', 'average_price': '15.00'},
        {'category': 'groceries', 'average_price': '7.50'},
    ]


def test_average_price_endpoint_reuses_cached_result() -> None:
    item = create_item('1', category='beauty', price='10.00')
    client = APIClient()

    first_response = client.get('/stats/avg-price-by-category')
    Item.objects.filter(pk=item.pk).update(price=Decimal('100.00'))
    second_response = client.get('/stats/avg-price-by-category')

    assert first_response.headers['X-Cache'] == 'MISS'
    assert second_response.headers['X-Cache'] == 'HIT'
    assert second_response.data == first_response.data


def test_changed_import_invalidates_average_price_cache(
    django_capture_on_commit_callbacks,
) -> None:
    initial_product = make_product(
        1,
        price=10,
        updated_at='2025-01-01T00:00:00Z',
    )
    updated_product = make_product(
        1,
        price=30,
        updated_at='2025-02-01T00:00:00Z',
    )

    with django_capture_on_commit_callbacks(execute=True):
        import_product_records([initial_product])

    client = APIClient()
    first_response = client.get('/stats/avg-price-by-category')
    cached_response = client.get('/stats/avg-price-by-category')

    with django_capture_on_commit_callbacks(execute=True):
        import_product_records([updated_product])

    refreshed_response = client.get('/stats/avg-price-by-category')

    assert first_response.headers['X-Cache'] == 'MISS'
    assert cached_response.headers['X-Cache'] == 'HIT'
    assert refreshed_response.headers['X-Cache'] == 'MISS'
    assert refreshed_response.data == [
        {'category': 'beauty', 'average_price': '30.00'},
    ]


def test_unchanged_import_keeps_average_price_cache(
    django_capture_on_commit_callbacks,
) -> None:
    product = make_product(
        1,
        price=10,
        updated_at='2025-01-01T00:00:00Z',
    )

    with django_capture_on_commit_callbacks(execute=True):
        import_product_records([product])

    client = APIClient()
    client.get('/stats/avg-price-by-category')

    with django_capture_on_commit_callbacks(execute=True):
        import_product_records([product])

    response = client.get('/stats/avg-price-by-category')

    assert response.headers['X-Cache'] == 'HIT'


def test_average_price_endpoint_bypasses_unavailable_redis() -> None:
    create_item('1', category='beauty', price='10.00')

    with patch(
        'items.services.statistics.cache.get',
        side_effect=RedisError('Redis is unavailable'),
    ):
        response = APIClient().get('/stats/avg-price-by-category')

    assert response.status_code == 200
    assert response.headers['X-Cache'] == 'BYPASS'
    assert response.data == [
        {'category': 'beauty', 'average_price': '10.00'},
    ]

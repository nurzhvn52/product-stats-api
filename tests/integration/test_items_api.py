from datetime import UTC, datetime
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from items.models import Item

pytestmark = pytest.mark.django_db


def create_item(external_id: str, *, category: str, price: str) -> Item:
    return Item.objects.create(
        source='test',
        external_id=external_id,
        name=f'Item {external_id}',
        category=category,
        price=Decimal(price),
        updated_at=datetime(2025, 1, 1, tzinfo=UTC),
    )


def test_items_endpoint_filters_by_category_and_price_range() -> None:
    create_item('1', category='beauty', price='9.99')
    expected = create_item('2', category='beauty', price='25.00')
    create_item('3', category='beauty', price='75.00')
    create_item('4', category='groceries', price='25.00')

    response = APIClient().get(
        '/items',
        {
            'category': 'beauty',
            'price_min': '10.00',
            'price_max': '50.00',
        },
    )

    assert response.status_code == 200
    assert response.data['count'] == 1
    assert [item['id'] for item in response.data['results']] == [expected.id]
    assert response.data['results'][0]['price'] == '25.00'


def test_items_endpoint_uses_inclusive_price_boundaries() -> None:
    lower = create_item('1', category='beauty', price='10.00')
    upper = create_item('2', category='beauty', price='20.00')
    create_item('3', category='beauty', price='20.01')

    response = APIClient().get(
        '/items',
        {'price_min': '10.00', 'price_max': '20.00'},
    )

    assert response.status_code == 200
    assert [item['id'] for item in response.data['results']] == [
        lower.id,
        upper.id,
    ]


def test_items_endpoint_paginates_results() -> None:
    for index in range(1, 6):
        create_item(str(index), category='beauty', price=str(index))

    response = APIClient().get('/items', {'page': 2, 'page_size': 2})

    assert response.status_code == 200
    assert response.data['count'] == 5
    assert len(response.data['results']) == 2
    assert response.data['previous'] is not None
    assert response.data['next'] is not None
    assert [item['external_id'] for item in response.data['results']] == ['3', '4']


@pytest.mark.parametrize(
    ('params', 'error_field'),
    [
        ({'price_min': 'invalid'}, 'price_min'),
        ({'price_min': '20', 'price_max': '10'}, 'price_max'),
        ({'page': '0'}, 'page'),
        ({'page_size': '101'}, 'page_size'),
    ],
)
def test_items_endpoint_rejects_invalid_query_parameters(
    params: dict,
    error_field: str,
) -> None:
    response = APIClient().get('/items', params)

    assert response.status_code == 400
    assert error_field in response.data


def test_items_endpoint_returns_not_found_for_missing_page() -> None:
    create_item('1', category='beauty', price='10.00')

    response = APIClient().get('/items', {'page': 2})

    assert response.status_code == 404

import pandas as pd
import pytest

from items.services.normalization import (
    NORMALIZED_COLUMNS,
    ProductNormalizationError,
    calculate_average_price_by_category,
    normalize_dummyjson_products,
)


def test_normalize_dummyjson_products_maps_and_cleans_fields() -> None:
    products = [
        {
            'id': '1',
            'title': '  Mascara  ',
            'category': '  Beauty  ',
            'price': '9.99',
            'meta': {'updatedAt': '2025-04-30T09:41:02.053Z'},
        },
    ]

    result = normalize_dummyjson_products(products)

    assert list(result.columns) == list(NORMALIZED_COLUMNS)
    assert result.loc[0, 'source'] == 'dummyjson'
    assert result.loc[0, 'external_id'] == '1'
    assert result.loc[0, 'name'] == 'Mascara'
    assert result.loc[0, 'category'] == 'beauty'
    assert result.loc[0, 'price'] == pytest.approx(9.99)
    assert result.loc[0, 'updated_at'] == pd.Timestamp('2025-04-30T09:41:02.053Z')


def test_normalize_drops_invalid_rows_and_keeps_newest_duplicate() -> None:
    products = [
        {
            'id': 1,
            'title': 'Old name',
            'category': 'beauty',
            'price': 10,
            'meta': {'updatedAt': '2025-01-01T00:00:00Z'},
        },
        {
            'id': 1,
            'title': 'New name',
            'category': 'beauty',
            'price': 12,
            'meta': {'updatedAt': '2025-02-01T00:00:00Z'},
        },
        {
            'id': 2,
            'title': '',
            'category': 'beauty',
            'price': 15,
            'meta': {'updatedAt': '2025-02-01T00:00:00Z'},
        },
        {
            'id': 3,
            'title': 'Invalid price',
            'category': 'beauty',
            'price': -1,
            'meta': {'updatedAt': '2025-02-01T00:00:00Z'},
        },
    ]

    result = normalize_dummyjson_products(products)

    assert len(result) == 1
    assert result.loc[0, 'external_id'] == '1'
    assert result.loc[0, 'name'] == 'New name'
    assert result.loc[0, 'price'] == pytest.approx(12)


def test_normalize_rejects_payload_with_missing_fields() -> None:
    products = [
        {
            'id': 1,
            'title': 'Incomplete product',
            'category': 'beauty',
            'price': 10,
        },
    ]

    with pytest.raises(ProductNormalizationError, match='meta.updatedAt'):
        normalize_dummyjson_products(products)


def test_normalize_empty_payload_returns_expected_columns() -> None:
    result = normalize_dummyjson_products([])

    assert result.empty
    assert list(result.columns) == list(NORMALIZED_COLUMNS)


def test_calculate_average_price_by_category() -> None:
    products = pd.DataFrame(
        [
            {'category': 'beauty', 'price': 10},
            {'category': 'beauty', 'price': 20},
            {'category': 'fragrances', 'price': 49.99},
        ]
    )

    result = calculate_average_price_by_category(products)

    assert result['category'].tolist() == ['beauty', 'fragrances']
    assert result['average_price'].tolist() == pytest.approx([15, 49.99])


def test_calculate_average_rejects_missing_columns() -> None:
    with pytest.raises(ProductNormalizationError, match='price'):
        calculate_average_price_by_category(pd.DataFrame([{'category': 'beauty'}]))

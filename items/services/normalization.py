from collections.abc import Sequence
from typing import Any

import pandas as pd

NORMALIZED_COLUMNS = (
    'source',
    'external_id',
    'name',
    'category',
    'price',
    'updated_at',
)
REQUIRED_DUMMYJSON_COLUMNS = {
    'id',
    'title',
    'category',
    'price',
    'meta.updatedAt',
}


class ProductNormalizationError(ValueError):
    pass


def empty_normalized_products() -> pd.DataFrame:
    return pd.DataFrame(columns=list(NORMALIZED_COLUMNS))


def normalize_dummyjson_products(products: Sequence[dict[str, Any]], source: str = 'dummyjson') -> pd.DataFrame:
    normalized_source = source.strip().lower()
    if not normalized_source:
        raise ProductNormalizationError('Product source name cannot be empty.')

    if not products:
        return empty_normalized_products()

    source_frame = pd.json_normalize(products, sep='.')
    missing_columns = REQUIRED_DUMMYJSON_COLUMNS.difference(source_frame.columns)
    if missing_columns:
        missing = ', '.join(sorted(missing_columns))
        raise ProductNormalizationError(f'DummyJSON payload is missing required fields: {missing}.')

    external_ids = pd.to_numeric(source_frame['id'], errors='coerce')
    valid_external_ids = (external_ids.notna() & external_ids.gt(0) & external_ids.mod(1).eq(0))

    normalized = pd.DataFrame(index=source_frame.index)
    normalized['source'] = normalized_source
    normalized['external_id'] = (external_ids.where(valid_external_ids).astype('Int64').astype('string'))
    normalized['name'] = source_frame['title'].astype('string').str.strip()
    normalized['category'] = source_frame['category'].astype('string').str.strip().str.lower()
    normalized['price'] = pd.to_numeric(source_frame['price'], errors='coerce').astype('float64')
    normalized['updated_at'] = pd.to_datetime(source_frame['meta.updatedAt'], errors='coerce', utc=True,)

    valid_rows = (
        normalized['external_id'].notna()
        & normalized['name'].notna()
        & normalized['name'].ne('')
        & normalized['category'].notna()
        & normalized['category'].ne('')
        & normalized['price'].notna()
        & normalized['price'].ge(0)
        & normalized['updated_at'].notna()
    )

    normalized = normalized.loc[valid_rows].copy()
    normalized = normalized.sort_values('updated_at', kind='stable')
    normalized = normalized.drop_duplicates(subset=['source', 'external_id'], keep='last',)
    normalized = normalized.sort_index().reset_index(drop=True)

    return normalized.loc[:, list(NORMALIZED_COLUMNS)]


def calculate_average_price_by_category(products: pd.DataFrame) -> pd.DataFrame:
    required_columns = {'category', 'price'}
    missing_columns = required_columns.difference(products.columns)
    if missing_columns:
        missing = ', '.join(sorted(missing_columns))
        raise ProductNormalizationError(f'Normalized products are missing required columns: {missing}.')

    prices = products.loc[:, ['category', 'price']].copy()
    prices['category'] = prices['category'].astype('string').str.strip()
    prices['price'] = pd.to_numeric(prices['price'], errors='coerce')
    prices = prices.dropna(subset=['category', 'price'])
    prices = prices.loc[prices['category'].ne('') & prices['price'].ge(0)]

    if prices.empty:
        return pd.DataFrame(columns=['category', 'average_price'])

    averages = (
        prices.groupby('category', as_index=False, sort=True)['price']
        .mean()
        .rename(columns={'price': 'average_price'})
    )
    averages['average_price'] = averages['average_price'].round(2)

    return averages

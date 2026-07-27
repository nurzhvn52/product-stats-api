import logging
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

import pandas as pd
from django.conf import settings
from django.core.cache import cache
from redis.exceptions import RedisError

from items.models import Item
from items.services.normalization import calculate_average_price_by_category

logger = logging.getLogger(__name__)

AVERAGE_PRICE_CACHE_KEY = 'stats:average-price-by-category:v1'
PRICE_QUANTUM = Decimal('0.01')
CacheStatus = Literal['HIT', 'MISS', 'BYPASS']


@dataclass(frozen=True, slots=True)
class AveragePriceStatistics:
    data: list[dict[str, str]]
    cache_status: CacheStatus


def calculate_average_price_statistics() -> list[dict[str, str]]:
    products = pd.DataFrame.from_records(
        Item.objects.values('category', 'price'),
        columns=['category', 'price'],
    )
    averages = calculate_average_price_by_category(products)

    return [
        {
            'category': row.category,
            'average_price': format(
                Decimal(str(row.average_price)).quantize(
                    PRICE_QUANTUM,
                    rounding=ROUND_HALF_UP,
                ),
                'f',
            ),
        }
        for row in averages.itertuples(index=False)
    ]


def get_average_price_statistics() -> AveragePriceStatistics:
    try:
        cached_data = cache.get(AVERAGE_PRICE_CACHE_KEY)
    except RedisError as error:
        logger.warning(
            'Redis cache is unavailable; average price statistics '
            'will not be cached: %s',
            error,
        )
        return AveragePriceStatistics(
            data=calculate_average_price_statistics(),
            cache_status='BYPASS',
        )

    if cached_data is not None:
        return AveragePriceStatistics(data=cached_data, cache_status='HIT')

    data = calculate_average_price_statistics()

    try:
        cache.set(
            AVERAGE_PRICE_CACHE_KEY,
            data,
            timeout=settings.AVG_PRICE_CACHE_TTL_SECONDS,
        )
    except RedisError as error:
        logger.warning(
            'Redis cache is unavailable; average price statistics were not cached: %s',
            error,
        )
        return AveragePriceStatistics(data=data, cache_status='BYPASS')

    return AveragePriceStatistics(data=data, cache_status='MISS')


def invalidate_average_price_cache() -> None:
    try:
        cache.delete(AVERAGE_PRICE_CACHE_KEY)
    except RedisError as error:
        logger.warning(
            'Redis cache is unavailable; average price statistics '
            'cache was not cleared: %s',
            error,
        )

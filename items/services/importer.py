import logging
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

import pandas as pd
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from items.models import Item
from items.services.normalization import normalize_dummyjson_products
from items.services.statistics import invalidate_average_price_cache

logger = logging.getLogger(__name__)
PRICE_QUANTUM = Decimal('0.01')
UPSERT_BATCH_SIZE = 500


@dataclass(frozen=True, slots=True)
class ImportResult:
    received: int
    normalized: int
    created: int
    updated: int
    unchanged: int

    @property
    def rejected(self) -> int:
        return self.received - self.normalized


@dataclass(frozen=True, slots=True)
class PersistenceResult:
    created: int
    updated: int
    unchanged: int


def _as_decimal(value: float) -> Decimal:
    return Decimal(str(value)).quantize(PRICE_QUANTUM, rounding=ROUND_HALF_UP)


def _as_datetime(value: object):
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    return value


def _build_items(products: pd.DataFrame) -> list[Item]:
    return [
        Item(
            source=row.source,
            external_id=row.external_id,
            name=row.name,
            category=row.category,
            price=_as_decimal(row.price),
            updated_at=_as_datetime(row.updated_at),
        )
        for row in products.itertuples(index=False)
    ]


def _load_existing_items(items: list[Item]) -> dict[tuple[str, str], Item]:
    query = Q(pk__in=[])
    external_ids_by_source: dict[str, list[str]] = {}

    for item in items:
        external_ids_by_source.setdefault(item.source, []).append(item.external_id)

    for source, external_ids in external_ids_by_source.items():
        query |= Q(source=source, external_id__in=external_ids)

    return {
        (item.source, item.external_id): item
        for item in Item.objects.select_for_update().filter(query)
    }


def _has_changes(existing: Item, incoming: Item) -> bool:
    return any(
        (
            existing.name != incoming.name,
            existing.category != incoming.category,
            existing.price != incoming.price,
            existing.updated_at != incoming.updated_at,
        )
    )


@transaction.atomic
def persist_normalized_products(products: pd.DataFrame) -> PersistenceResult:
    incoming_items = _build_items(products)
    if not incoming_items:
        return PersistenceResult(created=0, updated=0, unchanged=0)

    existing_items = _load_existing_items(incoming_items)
    items_to_create: list[Item] = []
    items_to_update: list[Item] = []
    unchanged = 0
    imported_at = timezone.now()

    for incoming in incoming_items:
        key = (incoming.source, incoming.external_id)
        existing = existing_items.get(key)

        if existing is None:
            items_to_create.append(incoming)
            continue

        if incoming.updated_at < existing.updated_at or not _has_changes(
            existing,
            incoming,
        ):
            unchanged += 1
            continue

        existing.name = incoming.name
        existing.category = incoming.category
        existing.price = incoming.price
        existing.updated_at = incoming.updated_at
        existing.imported_at = imported_at
        items_to_update.append(existing)

    Item.objects.bulk_create(
        items_to_create,
        batch_size=UPSERT_BATCH_SIZE,
    )
    Item.objects.bulk_update(
        items_to_update,
        fields=['name', 'category', 'price', 'updated_at', 'imported_at'],
        batch_size=UPSERT_BATCH_SIZE,
    )

    if items_to_create or items_to_update:
        transaction.on_commit(invalidate_average_price_cache, robust=True)

    return PersistenceResult(
        created=len(items_to_create),
        updated=len(items_to_update),
        unchanged=unchanged,
    )


def import_product_records(
    records: list[dict], source: str = 'dummyjson'
) -> ImportResult:
    normalized_products = normalize_dummyjson_products(records, source=source)
    persistence = persist_normalized_products(normalized_products)
    result = ImportResult(
        received=len(records),
        normalized=len(normalized_products),
        created=persistence.created,
        updated=persistence.updated,
        unchanged=persistence.unchanged,
    )

    logger.info(
        'Product import completed: received=%d normalized=%d rejected=%d '
        'created=%d updated=%d unchanged=%d',
        result.received,
        result.normalized,
        result.rejected,
        result.created,
        result.updated,
        result.unchanged,
    )

    return result

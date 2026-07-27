import logging

from celery import shared_task
from django.conf import settings
from redis import Redis
from redis.exceptions import RedisError
from redis.lock import Lock

from items.services.importer import ImportResult, import_product_records
from items.services.sources import ProductSourceError, fetch_dummyjson_products

logger = logging.getLogger(__name__)

IMPORT_LOCK_KEY = 'locks:dummyjson-product-import'


def _create_import_lock() -> Lock:
    redis_client = Redis.from_url(settings.CELERY_BROKER_URL)
    return redis_client.lock(
        IMPORT_LOCK_KEY,
        timeout=settings.CELERY_IMPORT_LOCK_TIMEOUT_SECONDS,
    )


def _serialize_result(result: ImportResult) -> dict[str, int | str]:
    return {
        'status': 'completed',
        'received': result.received,
        'normalized': result.normalized,
        'rejected': result.rejected,
        'created': result.created,
        'updated': result.updated,
        'unchanged': result.unchanged,
    }


@shared_task(
    name='items.import_dummyjson_products',
    autoretry_for=(ProductSourceError, RedisError),
    retry_backoff=5,
    retry_backoff_max=60,
    retry_jitter=True,
    retry_kwargs={'max_retries': 3},
)
def import_dummyjson_products() -> dict[str, int | str]:
    import_lock = _create_import_lock()
    if not import_lock.acquire(blocking=False):
        logger.info('Product import skipped because another import is running.')
        return {
            'status': 'skipped',
            'reason': 'already_running',
        }

    try:
        records = fetch_dummyjson_products(
            url=settings.DUMMYJSON_PRODUCTS_URL,
            timeout=settings.DUMMYJSON_TIMEOUT_SECONDS,
        )
        result = import_product_records(records)
        task_result = _serialize_result(result)
        logger.info(
            'Scheduled product import completed: created=%d updated=%d unchanged=%d',
            result.created,
            result.updated,
            result.unchanged,
        )
        return task_result
    finally:
        try:
            import_lock.release()
        except RedisError as error:
            logger.warning('Unable to release product import lock: %s', error)

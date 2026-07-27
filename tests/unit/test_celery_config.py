from datetime import timedelta

from django.conf import settings

from config.celery import app


def test_celery_discovers_scheduled_import_task() -> None:
    app.autodiscover_tasks(force=True)

    assert 'items.import_dummyjson_products' in app.tasks


def test_beat_schedule_uses_configured_interval() -> None:
    schedule = settings.CELERY_BEAT_SCHEDULE['import-dummyjson-products']

    assert schedule['task'] == 'items.import_dummyjson_products'
    assert schedule['schedule'] == timedelta(
        minutes=settings.CELERY_IMPORT_INTERVAL_MINUTES
    )

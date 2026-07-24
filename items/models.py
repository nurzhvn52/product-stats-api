from django.db import models


class Item(models.Model):
    source = models.CharField(max_length=50)
    external_id = models.CharField(max_length=128)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=128)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    updated_at = models.DateTimeField()
    imported_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(
                fields=['source', 'external_id'],
                name='items_item_source_external_id_uniq',
            ),
            models.CheckConstraint(
                condition=models.Q(price__gte=0),
                name='items_item_price_nonnegative',
            ),
        ]
        indexes = [
            models.Index(
                fields=['category', 'price'],
                name='items_category_price_idx',
            ),
            models.Index(fields=['price'], name='items_price_idx'),
        ]

    def __str__(self) -> str:
        return f'{self.name} ({self.source}:{self.external_id})'

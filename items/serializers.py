from decimal import Decimal

from rest_framework import serializers

from items.models import Item


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = [
            'id',
            'source',
            'external_id',
            'name',
            'category',
            'price',
            'updated_at',
        ]


class ItemListQuerySerializer(serializers.Serializer):
    category = serializers.CharField(required=False, allow_blank=False, max_length=128,)
    price_min = serializers.DecimalField(required=False, min_value=Decimal('0'), max_digits=12, decimal_places=2,)
    price_max = serializers.DecimalField(required=False, min_value=Decimal('0'), max_digits=12, decimal_places=2,)
    page = serializers.IntegerField(required=False, min_value=1)
    page_size = serializers.IntegerField(required=False, min_value=1, max_value=100,)

    def validate(self, attrs: dict) -> dict:
        price_min = attrs.get('price_min')
        price_max = attrs.get('price_max')

        if price_min is not None and price_max is not None and price_min > price_max:
            raise serializers.ValidationError(
                {
                    'price_max': ('Must be greater than or equal to price_min.'),
                }
            )

        return attrs

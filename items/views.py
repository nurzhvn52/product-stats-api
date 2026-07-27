from django.db.models import QuerySet
from rest_framework.generics import ListAPIView

from items.models import Item
from items.pagination import ItemPagination
from items.serializers import ItemListQuerySerializer, ItemSerializer


class ItemListView(ListAPIView):
    serializer_class = ItemSerializer
    pagination_class = ItemPagination

    def get_queryset(self) -> QuerySet[Item]:
        query_serializer = ItemListQuerySerializer(
            data=self.request.query_params,
        )
        query_serializer.is_valid(raise_exception=True)
        filters = query_serializer.validated_data

        queryset = Item.objects.all()

        if category := filters.get('category'):
            queryset = queryset.filter(category=category)

        if (price_min := filters.get('price_min')) is not None:
            queryset = queryset.filter(price__gte=price_min)

        if (price_max := filters.get('price_max')) is not None:
            queryset = queryset.filter(price__lte=price_max)

        return queryset

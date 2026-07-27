from django.urls import path

from items.views import AveragePriceByCategoryView, ItemListView

urlpatterns = [
    path('items', ItemListView.as_view(), name='item-list'),
    path(
        'stats/avg-price-by-category',
        AveragePriceByCategoryView.as_view(),
        name='average-price-by-category',
    ),
]

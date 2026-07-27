from django.urls import path

from items.views import ItemListView

urlpatterns = [
    path('items', ItemListView.as_view(), name='item-list'),
]

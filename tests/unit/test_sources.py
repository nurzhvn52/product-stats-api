from pathlib import Path
from unittest.mock import Mock

import pytest
import requests

from items.services.sources import (
    DEFAULT_DUMMYJSON_PRODUCTS_URL,
    ProductSourceError,
    ProductSourceFormatError,
    fetch_dummyjson_products,
    load_json_products,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_load_json_products_reads_repository_sample() -> None:
    products = load_json_products(PROJECT_ROOT / 'data' / 'sample_products.json')

    assert len(products) == 10
    assert products[0]['id'] == 1
    assert products[0]['title'] == 'Essence Mascara Lash Princess'


def test_fetch_dummyjson_products_returns_product_array() -> None:
    response = Mock()
    response.json.return_value = {'products': [{'id': 1}]}
    session = Mock(spec=requests.Session)
    session.get.return_value = response

    products = fetch_dummyjson_products(timeout=5, session=session)

    assert products == [{'id': 1}]
    session.get.assert_called_once_with(
        DEFAULT_DUMMYJSON_PRODUCTS_URL,
        timeout=5,
    )
    response.raise_for_status.assert_called_once_with()


def test_fetch_dummyjson_products_wraps_network_errors() -> None:
    session = Mock(spec=requests.Session)
    session.get.side_effect = requests.Timeout('request timed out')

    with pytest.raises(ProductSourceError, match='Unable to fetch'):
        fetch_dummyjson_products(session=session)


def test_fetch_dummyjson_products_rejects_invalid_payload() -> None:
    response = Mock()
    response.json.return_value = {'unexpected': []}
    session = Mock(spec=requests.Session)
    session.get.return_value = response

    with pytest.raises(ProductSourceFormatError, match='products array'):
        fetch_dummyjson_products(session=session)

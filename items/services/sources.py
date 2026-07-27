import json
from pathlib import Path
from typing import Any

import requests

DEFAULT_DUMMYJSON_PRODUCTS_URL = 'https://dummyjson.com/products?limit=0'
DEFAULT_TIMEOUT_SECONDS = 10.0


class ProductSourceError(Exception):
    pass


class ProductSourceFormatError(ProductSourceError):
    pass


def extract_products(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        products = payload.get('products')
    elif isinstance(payload, list):
        products = payload
    else:
        raise ProductSourceFormatError(
            'Product source must contain a JSON object or array.'
        )

    if not isinstance(products, list):
        raise ProductSourceFormatError('Product source must contain a products array.')

    if not all(isinstance(product, dict) for product in products):
        raise ProductSourceFormatError(
            'Every product in the source must be a JSON object.'
        )

    return products


def fetch_dummyjson_products(url: str = DEFAULT_DUMMYJSON_PRODUCTS_URL, timeout: float = DEFAULT_TIMEOUT_SECONDS, session: requests.Session | None = None) -> list[dict[str, Any]]:
    owns_session = session is None
    client = session or requests.Session()

    try:
        response = client.get(url, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise ProductSourceError(f'Unable to fetch products from {url}.') from exc
    finally:
        if owns_session:
            client.close()

    try:
        payload = response.json()
    except ValueError as exc:
        raise ProductSourceFormatError('Product source returned invalid JSON.') from exc

    return extract_products(payload)


def load_json_products(path: str | Path) -> list[dict[str, Any]]:
    source_path = Path(path)

    try:
        with source_path.open(encoding='utf-8') as source_file:
            payload = json.load(source_file)
    except OSError as exc:
        raise ProductSourceError(
            f'Unable to read product source {source_path}.'
        ) from exc
    except json.JSONDecodeError as exc:
        raise ProductSourceFormatError(
            f'Product source {source_path} contains invalid JSON.'
        ) from exc

    return extract_products(payload)

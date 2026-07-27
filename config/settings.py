import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


def get_bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    return value.lower() in {'1', 'true', 'yes', 'on'}


def get_list_env(name: str, default: str = '') -> list[str]:
    return [
        value.strip() for value in os.getenv(name, default).split(',') if value.strip()
    ]


SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'unsafe-development-secret-key')
DEBUG = get_bool_env('DJANGO_DEBUG', default=False)
ALLOWED_HOSTS = get_list_env(
    'DJANGO_ALLOWED_HOSTS',
    default='localhost,127.0.0.1',
)

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'rest_framework',
    'items',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'product_statistics'),
        'USER': os.getenv('POSTGRES_USER', 'product_statistics'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'product_statistics'),
        'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
        'CONN_MAX_AGE': 60,
    }
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

APPEND_SLASH = False

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

DUMMYJSON_PRODUCTS_URL = os.getenv(
    'DUMMYJSON_PRODUCTS_URL',
    'https://dummyjson.com/products?limit=0',
)
DUMMYJSON_TIMEOUT_SECONDS = float(
    os.getenv('DUMMYJSON_TIMEOUT_SECONDS', '10'),
)

"""
Django settings for demo_project.

This demo project showcases django-ollama namespace features.
"""

from pathlib import Path
import os
import sys

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Add parent directory to path so we can import django_ollama
sys.path.insert(0, str(BASE_DIR.parent / 'src'))

# Security settings
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-demo-key-for-testing-only-do-not-use-in-production')

DEBUG = os.environ.get('DJANGO_DEBUG', 'true').lower() == 'true'

# Get domain from environment or use default
DOMAIN = os.environ.get('DOMAIN', 'django-ollama.l.supported.systems')

# Build ALLOWED_HOSTS including the domain
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0', DOMAIN]
# Add any additional hosts from environment
if os.environ.get('ALLOWED_HOSTS'):
    ALLOWED_HOSTS.extend(os.environ.get('ALLOWED_HOSTS').split(','))

# CSRF trusted origins for HTTPS
CSRF_TRUSTED_ORIGINS = [
    f'https://{DOMAIN}',
    f'http://{DOMAIN}',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Our apps
    'channels',
    'django_ollama',
    'knowledge_demo',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_ollama.context_injection.AIContextMiddleware',  # Add context injection middleware
]

ROOT_URLCONF = 'demo_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'demo_project.wsgi.application'
ASGI_APPLICATION = 'demo_project.asgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db' / 'db.sqlite3',
    }
}

# Channels configuration for WebSocket support
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [os.environ.get('REDIS_URL', 'redis://redis:6379/0')],
        },
    } if not DEBUG else {
        'BACKEND': 'channels.layers.InMemoryChannelLayer'
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django-Ollama configuration
DJANGO_OLLAMA_OLLAMA_HOST = os.environ.get('DJANGO_OLLAMA_OLLAMA_HOST', 'http://localhost:11434')
DJANGO_OLLAMA_OLLAMA_DEFAULT_MODEL = os.environ.get('DJANGO_OLLAMA_OLLAMA_DEFAULT_MODEL', 'llama3.2:1b')
DJANGO_OLLAMA_OLLAMA_TIMEOUT = 60
DJANGO_OLLAMA_CONTEXT_INJECTION_ENABLED = True
DJANGO_OLLAMA_CONTEXT_INJECTION_MAX_ITEMS = 25
DJANGO_OLLAMA_ENABLE_STREAMING_RESPONSES = True
DJANGO_OLLAMA_WEBSOCKET_MESSAGE_SIZE_LIMIT = 2 * 1024 * 1024  # 2MB
DJANGO_OLLAMA_RATE_LIMIT_REQUESTS_PER_MINUTE = 30  # Lower for demo

# Django-Ollama namespace configuration
DJANGO_OLLAMA_NAMESPACE_POLICY = 'django_ollama.namespace_security.DefaultNamespacePolicy'

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django_ollama': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
        },
        'knowledge_demo': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
        },
    },
}
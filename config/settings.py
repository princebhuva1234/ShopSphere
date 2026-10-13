from pathlib import Path
import os

import dj_database_url
from dotenv import load_dotenv


# =========================================================
# BASE DIRECTORY
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# =========================================================
# ENVIRONMENT VARIABLES
# =========================================================

load_dotenv(BASE_DIR / '.env')

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL")

# =========================================================
# SECURITY
# =========================================================

SECRET_KEY = os.getenv(
    'SECRET_KEY',
    'django-insecure-development-only-change-this'
)


DEBUG = os.getenv(
    'DEBUG',
    'True'
).lower() == 'true'


# ---------------------------------------------------------
# ALLOWED HOSTS
# ---------------------------------------------------------

ALLOWED_HOSTS = [
    '127.0.0.1',
    'localhost',
]


# Render automatically provides this variable.
RENDER_EXTERNAL_HOSTNAME = os.getenv(
    'RENDER_EXTERNAL_HOSTNAME'
)

if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(
        RENDER_EXTERNAL_HOSTNAME
    )


# Optional custom domain(s)
EXTRA_ALLOWED_HOSTS = os.getenv(
    'ALLOWED_HOSTS',
    ''
)

if EXTRA_ALLOWED_HOSTS:

    ALLOWED_HOSTS.extend(
        host.strip()
        for host in EXTRA_ALLOWED_HOSTS.split(',')
        if host.strip()
    )


# Optional ngrok hostname for local testing.
NGROK_HOST = os.getenv(
    'NGROK_HOST'
)

if NGROK_HOST:
    ALLOWED_HOSTS.append(
        NGROK_HOST
    )


# Remove duplicates
ALLOWED_HOSTS = list(
    dict.fromkeys(ALLOWED_HOSTS)
)


# =========================================================
# APPLICATIONS
# =========================================================

INSTALLED_APPS = [

    # Django built-in applications
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # ShopSphere applications
    'accounts',
    'categories',
    'products',
    'payments',
    'cart',
    'coupons',
    'orders',
    'wishlist',
    'reviews',
    'returns',
    'dashboard',




    # Third-party applications
    'rest_framework',
]


# =========================================================
# MIDDLEWARE
# =========================================================

MIDDLEWARE = [

    'django.middleware.security.SecurityMiddleware',

    # WhiteNoise serves static files in production.
    'whitenoise.middleware.WhiteNoiseMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',

    'django.middleware.common.CommonMiddleware',

    'django.middleware.csrf.CsrfViewMiddleware',

    'django.contrib.auth.middleware.AuthenticationMiddleware',

    'django.contrib.messages.middleware.MessageMiddleware',

    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# =========================================================
# URL CONFIGURATION
# =========================================================

ROOT_URLCONF = 'config.urls'


# =========================================================
# TEMPLATES
# =========================================================

TEMPLATES = [

    {
        'BACKEND':
            'django.template.backends.django.DjangoTemplates',

        'DIRS': [
            BASE_DIR / 'templates'
        ],

        'APP_DIRS': True,

        'OPTIONS': {

            'context_processors': [

                'django.template.context_processors.request',

                'django.contrib.auth.context_processors.auth',

                'django.contrib.messages.context_processors.messages',

            ],
        },
    },
]


# =========================================================
# WSGI / ASGI
# =========================================================

WSGI_APPLICATION = 'config.wsgi.application'


# =========================================================
# DATABASE
# =========================================================

DATABASE_URL = os.getenv(
    'DATABASE_URL'
)


if DATABASE_URL:

    # Production / Render PostgreSQL
    DATABASES = {

        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
        )

    }

else:

    # Local PostgreSQL
    DATABASES = {

        'default': {

            'ENGINE':
                'django.db.backends.postgresql',

            'NAME':
                os.getenv(
                    'DB_NAME',
                    'shopsphere_db'
                ),

            'USER':
                os.getenv(
                    'DB_USER',
                    'postgres'
                ),

            'PASSWORD':
                os.getenv(
                    'DB_PASSWORD',
                    'prince'
                ),

            'HOST':
                os.getenv(
                    'DB_HOST',
                    'localhost'
                ),

            'PORT':
                os.getenv(
                    'DB_PORT',
                    '5432'
                ),
        }

    }


# =========================================================
# CUSTOM USER MODEL
# =========================================================

AUTH_USER_MODEL = 'accounts.User'


# =========================================================
# PASSWORD VALIDATION
# =========================================================

AUTH_PASSWORD_VALIDATORS = [

    {
        'NAME':
            'django.contrib.auth.password_validation.'
            'UserAttributeSimilarityValidator',
    },

    {
        'NAME':
            'django.contrib.auth.password_validation.'
            'MinimumLengthValidator',
    },

    {
        'NAME':
            'django.contrib.auth.password_validation.'
            'CommonPasswordValidator',
    },

    {
        'NAME':
            'django.contrib.auth.password_validation.'
            'NumericPasswordValidator',
    },

]


# =========================================================
# INTERNATIONALIZATION
# =========================================================

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Kolkata'

USE_I18N = True

USE_TZ = True


# =========================================================
# STATIC FILES
# =========================================================

STATIC_URL = '/static/'

STATIC_ROOT = BASE_DIR / 'staticfiles'


# Only add the project's root static directory if it exists.
STATIC_DIR = BASE_DIR / 'static'

if STATIC_DIR.exists():

    STATICFILES_DIRS = [
        STATIC_DIR
    ]

else:

    STATICFILES_DIRS = []


# =========================================================
# FILE STORAGE
# =========================================================

STORAGES = {

    'default': {

        'BACKEND':
            'django.core.files.storage.FileSystemStorage',

    },

    'staticfiles': {

        'BACKEND':
            'django.contrib.staticfiles.storage.StaticFilesStorage',

    },

}


# Use compressed, hashed static files in production.
if not DEBUG:

    STORAGES['staticfiles'] = {

        'BACKEND':
            'whitenoise.storage.'
            'CompressedManifestStaticFilesStorage',

    }


# =========================================================
# MEDIA FILES
# =========================================================

MEDIA_URL = '/media/'

MEDIA_ROOT = BASE_DIR / 'media'


# =========================================================
# DEFAULT PRIMARY KEY
# =========================================================

DEFAULT_AUTO_FIELD = (
    'django.db.models.BigAutoField'
)


# =========================================================
# LOGIN / LOGOUT
# =========================================================

LOGIN_URL = '/accounts/login/'

LOGIN_REDIRECT_URL = '/'

LOGOUT_REDIRECT_URL = '/'


# =========================================================
# DJANGO REST FRAMEWORK
# =========================================================

REST_FRAMEWORK = {

    'DEFAULT_PERMISSION_CLASSES': [

        'rest_framework.permissions.AllowAny',

    ],

}


# =========================================================
# RAZORPAY
# =========================================================

RAZORPAY_KEY_ID = os.getenv(
    'RAZORPAY_KEY_ID'
)

RAZORPAY_KEY_SECRET = os.getenv(
    'RAZORPAY_KEY_SECRET'
)

RAZORPAY_WEBHOOK_SECRET = os.getenv(
    'RAZORPAY_WEBHOOK_SECRET'
)


# =========================================================
# CSRF TRUSTED ORIGINS
# =========================================================

CSRF_TRUSTED_ORIGINS = [

    'http://127.0.0.1:8000',
    'http://localhost:8000',

]


RENDER_EXTERNAL_HOSTNAME = os.getenv(
    'RENDER_EXTERNAL_HOSTNAME'
)

if RENDER_EXTERNAL_HOSTNAME:

    CSRF_TRUSTED_ORIGINS.append(
        f'https://{RENDER_EXTERNAL_HOSTNAME}'
    )


EXTRA_CSRF_ORIGINS = os.getenv(
    'CSRF_TRUSTED_ORIGINS',
    ''
)

if EXTRA_CSRF_ORIGINS:

    CSRF_TRUSTED_ORIGINS.extend(
        origin.strip()
        for origin in EXTRA_CSRF_ORIGINS.split(',')
        if origin.strip()
    )


CSRF_TRUSTED_ORIGINS = list(
    dict.fromkeys(CSRF_TRUSTED_ORIGINS)
)


# =========================================================
# PRODUCTION SECURITY
# =========================================================

if not DEBUG:

    # HTTPS
    SECURE_SSL_REDIRECT = True

    SECURE_PROXY_SSL_HEADER = (
        'HTTP_X_FORWARDED_PROTO',
        'https'
    )

    # Secure cookies
    SESSION_COOKIE_SECURE = True

    CSRF_COOKIE_SECURE = True

    # Clickjacking protection
    X_FRAME_OPTIONS = 'DENY'

    # MIME sniffing protection
    SECURE_CONTENT_TYPE_NOSNIFF = True

    # HSTS
    SECURE_HSTS_SECONDS = 31536000

    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

    SECURE_HSTS_PRELOAD = True

    # Referrer policy
    SECURE_REFERRER_POLICY = (
        'strict-origin-when-cross-origin'
    )


# =========================================================
# EMAIL
# =========================================================

DEFAULT_FROM_EMAIL = os.getenv(
    'DEFAULT_FROM_EMAIL',
    'no-reply@shopsphere.com'
)

SERVER_EMAIL = os.getenv(
    'SERVER_EMAIL',
    'server@shopsphere.com'
)


# =====================================================
# GMAIL SMTP EMAIL CONFIGURATION
# =====================================================

MAILERS = {
    'default': {
        'BACKEND': 'django.core.mail.backends.smtp.EmailBackend',

        'OPTIONS': {
            'host': 'smtp.gmail.com',
            'port': 465,

            # Secure SSL connection
            'use_ssl': True,
            'use_tls': False,

            # Gmail credentials from .env
            'username': os.getenv(
                'EMAIL_HOST_USER', ''
            ).strip(),

            'password': os.getenv(
                'EMAIL_HOST_PASSWORD', ''
            ).replace(' ', '').strip(),

            'timeout': 30,
        },
    },
}

DEFAULT_FROM_EMAIL = os.getenv(
    'DEFAULT_FROM_EMAIL',
    os.getenv('EMAIL_HOST_USER', '')
).strip()



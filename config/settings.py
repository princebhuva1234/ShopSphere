from pathlib import Path
import os
from dotenv import load_dotenv



# --------------------------------------------------
# BASE DIRECTORY
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

# --------------------------------------------------
# LOAD .ENV FILE
# --------------------------------------------------



# --------------------------------------------------
# SECURITY
# --------------------------------------------------

SECRET_KEY = 'django-insecure-change-this-later'

DEBUG = True

ALLOWED_HOSTS = [
    '127.0.0.1',
    'localhost',
    'pliable-prior-overflow.ngrok-free.dev',
]

# --------------------------------------------------
# APPLICATIONS
# --------------------------------------------------

INSTALLED_APPS = [

    # Django built-in apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # ShopSphere apps
    'accounts',
    'categories',
    'products',
    'payments',
    'cart',
    'orders',

    # Third-party apps
    'rest_framework',
]


# --------------------------------------------------
# MIDDLEWARE
# --------------------------------------------------

MIDDLEWARE = [

    'django.middleware.security.SecurityMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',

    'django.middleware.common.CommonMiddleware',

    'django.middleware.csrf.CsrfViewMiddleware',

    'django.contrib.auth.middleware.AuthenticationMiddleware',

    'django.contrib.messages.middleware.MessageMiddleware',

    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# --------------------------------------------------
# URL CONFIGURATION
# --------------------------------------------------

ROOT_URLCONF = 'config.urls'


# --------------------------------------------------
# TEMPLATES
# --------------------------------------------------

TEMPLATES = [

    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',

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


# --------------------------------------------------
# WSGI
# --------------------------------------------------

WSGI_APPLICATION = 'config.wsgi.application'


# --------------------------------------------------
# DATABASE
# --------------------------------------------------

DATABASES = {

    'default': {

        'ENGINE': 'django.db.backends.postgresql',

        'NAME': 'shopsphere_db',

        'USER': 'postgres',

        'PASSWORD': 'prince',

        'HOST': 'localhost',

        'PORT': '5432',
    }
}


# --------------------------------------------------
# CUSTOM USER MODEL
# --------------------------------------------------

AUTH_USER_MODEL = 'accounts.User'


# --------------------------------------------------
# PASSWORD VALIDATION
# --------------------------------------------------

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


# --------------------------------------------------
# INTERNATIONALIZATION
# --------------------------------------------------

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Kolkata'

USE_I18N = True

USE_TZ = True


# --------------------------------------------------
# STATIC FILES
# --------------------------------------------------

STATIC_URL = 'static/'

STATICFILES_DIRS = [
    BASE_DIR / 'static'
]


# --------------------------------------------------
# MEDIA FILES
# --------------------------------------------------

MEDIA_URL = '/media/'

MEDIA_ROOT = BASE_DIR / 'media'


# --------------------------------------------------
# DEFAULT PRIMARY KEY
# --------------------------------------------------

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# --------------------------------------------------
# LOGIN / LOGOUT
# --------------------------------------------------

LOGIN_URL = '/accounts/login/'

LOGIN_REDIRECT_URL = '/'

LOGOUT_REDIRECT_URL = '/'


# --------------------------------------------------
# DJANGO REST FRAMEWORK
# --------------------------------------------------

REST_FRAMEWORK = {

    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
}


# --------------------------------------------------
# RAZORPAY
# --------------------------------------------------

# --------------------------------------------------
# RAZORPAY
# --------------------------------------------------

RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID')

RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET')

RAZORPAY_WEBHOOK_SECRET = os.getenv(
    'RAZORPAY_WEBHOOK_SECRET'
)
"""
Django settings for LYS_schoolapp project.
"""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# =====================================================
# Security
# =====================================================

SECRET_KEY = 'django-insecure-m@j5%!iwq4p@)oj0_*$wn0)v4wfoy7@gf=r#)naezp$2pzw+e&'

DEBUG = True

ALLOWED_HOSTS = ['*']

# =====================================================
# Applications
# =====================================================

INSTALLED_APPS = [
    # Django apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    # Third-party apps
    'django_extensions',
    'crispy_forms',
    'crispy_bootstrap5',
    'import_export',

    # Project apps
    'account',
    'students',
    'report',
    'payments',
    'school_settings',
    'home',
    'books_inventory',
    # 'uniforms_inventory',
    'treasury_management',
]

# =====================================================
# Middleware
# =====================================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',

    'LYS_schoolapp.middleware.AdminEnglishSiteArabicMiddleware',

    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'LYS_schoolapp.urls'

# =====================================================
# Templates
# =====================================================

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',

                # صلاحيات الخزينة في القوالب
                'treasury_management.context_processors.treasury_permissions',
            ],
        },
    },
]

WSGI_APPLICATION = 'LYS_schoolapp.wsgi.application'

# =====================================================
# Database
# =====================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# =====================================================
# Custom user model
# =====================================================

AUTH_USER_MODEL = 'account.User'

# =====================================================
# Password validation
# =====================================================

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

# =====================================================
# Internationalization
# =====================================================

# LANGUAGE_CODE = 'ar'
TIME_ZONE = 'Africa/Cairo'
USE_I18N = True
USE_TZ = True

# =====================================================
# Crispy Forms
# =====================================================

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# =====================================================
# Static and media files
# =====================================================

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# =====================================================
# Auth redirects
# =====================================================

LOGIN_URL = 'account:login'

# بعد تسجيل الدخول الأفضل يروح للصفحة الرئيسية وليس صفحة تسجيل الدخول مرة أخرى
LOGIN_REDIRECT_URL = 'home:home'  # لو اسم رابط الصفحة الرئيسية مختلف عدله حسب home/urls.py

LOGOUT_REDIRECT_URL = 'account:login'

# =====================================================
# Default primary key
# =====================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =====================================================
# Logging
# =====================================================

# مهم جداً: إنشاء فولدر logs قبل تفعيل FileHandler
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name}: {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname}: {message}',
            'style': '{',
        },
    },

    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'treasury_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': LOGS_DIR / 'treasury_permissions.log',
            'formatter': 'verbose',
            'encoding': 'utf-8',
        },
    },

    'loggers': {
        'treasury_management.decorators': {
            'handlers': ['console', 'treasury_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'school_settings': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

FORMS_URLFIELD_ASSUME_HTTPS = True
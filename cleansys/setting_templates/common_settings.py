"""

"""

import os
from django.urls import reverse_lazy

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE_URL = '/'
HOST = 'http://127.0.0.1'  # This is for links in emails, must not end with a slash

# If WSGIScriptAlias of your Apache config already implements the base url, set to False
APPLY_BASE_URL_TO_URL_PATTERNS = True

DUTYSWITCH_HAS_CRON = True

# Application definition

INSTALLED_APPS = [
    # 'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'webinterface.apps.WebinterfaceConfig',
    'bootstrap3',
    'crispy_forms',
    'coverage',
    'rest_framework'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'cleansys.urls'
LOGIN_URL = reverse_lazy('webinterface:login-by-click')
LOGIN_REDIRECT_URL = reverse_lazy('webinterface:cleaner-no-page')
LOGOUT_REDIRECT_URL = reverse_lazy('webinterface:welcome')


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'cleansys.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = 'de-de'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

LOGGING_PATH = os.path.join(BASE_DIR, 'logs')
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'file_format': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {  # Schedule model builds its loggers with this handler
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'maxBytes': 1000000,
            'backupCount': 3,
            'filename': os.path.join(LOGGING_PATH, 'general.log'),
            'formatter': 'file_format',
            'encoding': 'utf8',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
            'filters': ['require_debug_false'],
        }
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'propagate': True,
        },
        'file_logger': {
            'handlers': ['file'],
            'level': 'INFO',
        }
    }
}  # Further logging configuration is added in dev_settings and prod_settings


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/
STATIC_DIR = 'static/'
STATIC_URL = os.path.join(BASE_URL, STATIC_DIR)
STATIC_ROOT = os.path.join(BASE_DIR, STATIC_DIR)

MEDIA_DIR = 'media/'
MEDIA_URL = os.path.join(BASE_URL, MEDIA_DIR)
MEDIA_ROOT = os.path.join(BASE_DIR, MEDIA_DIR)

PLOT_PATH = os.path.join(MEDIA_ROOT)
CLEANER_ANALYTICS_FILE = os.path.join(PLOT_PATH, 'cleaner_analytics.html')


CRISPY_TEMPLATE_PACK = 'bootstrap3'
BOOTSTRAP3 = {
    # The URL to the jQuery JavaScript file
    'jquery_url': STATIC_URL + '/webinterface/jquery/jquery.min.js',

    # The Bootstrap base URL
    'base_url': STATIC_URL + '/webinterface/bootstrap-3.4.1-dist/',

    # The complete URL to the Bootstrap CSS file (None means no theme)
    # 'theme_url': STATIC_URL + '/webinterface/bootstrap-3.4.1-dist/css/bootstrap-theme.css',
}

REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10
}

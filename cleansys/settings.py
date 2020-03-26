"""

"""

import os
import logging
from django.urls import reverse_lazy


logging.getLogger('').setLevel(logging.DEBUG)

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

with open('cleansys/keys/django-secret-key.txt', 'r') as secret_key_file:
    SECRET_KEY = secret_key_file.read().replace('\n', '')

with open('cleansys/keys/slack-bot-token.txt', 'r') as slack_bot_token:
    SLACK_BOT_TOKEN = slack_bot_token.read().replace('\n', '')

os.environ['SLACK_BOT_TOKEN'] = SLACK_BOT_TOKEN

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
ABSOLUTE_TRUST_IN_USERS = True

ALLOWED_HOSTS = []

LOGIN_URL = reverse_lazy('webinterface:login-by-click')
LOGIN_REDIRECT_URL = reverse_lazy('webinterface:cleaner-no-page')
LOGOUT_REDIRECT_URL = '/'


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'webinterface.apps.WebinterfaceConfig',
    'slackbot.apps.SlackbotConfig',
    'bootstrap3',
    'crispy_forms',
    'slack',
    'django_celery_beat',
    'django_celery_results',
    'coverage'
]

CRISPY_TEMPLATE_PACK = 'bootstrap3'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'putzplan_generator.urls'

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
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = 'de-de'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

STATIC_URL = '/static/'

# Celery settings

CELERY_RESULT_BACKEND = 'django-db'
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers.DatabaseScheduler"
CELERY_WORKER_CONCURRENCY = 1  # Alternative: Manual Routing: Only one worker for poll_slack queue

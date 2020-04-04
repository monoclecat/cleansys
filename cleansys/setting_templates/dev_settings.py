"""
Development settings. NOT FOR PRODUCTION.
"""
from .common_settings import LOGGING

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "iE]L3?gXE$UG`#C'h'L:U*S58}vYkt;z2H3H&d`uX-3D,nak/E$8+D]g"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# For later implementation, when login-by-click is wished to be replaced with a standard login
# ABSOLUTE_TRUST_IN_USERS = True

# If the last Assignment of a Schedule is only these many weeks away from current_epoch_week, a warning is displayed
WARN_WEEKS_IN_ADVANCE__ASSIGNMENTS_RUNNING_OUT = 4


# Email settings
EMAIL_HOST = 'localhost'
EMAIL_HOST_USER = 'system@cleansys.headquarters'
EMAIL_HOST_PASSWORD = 'areallygoodpassword'
EMAIL_FROM_ADDRESS = 'system@cleansys.headquarters'
SERVER_EMAIL = EMAIL_FROM_ADDRESS
DEFAULT_FROM_EMAIL = EMAIL_FROM_ADDRESS
EMAIL_PORT = 587
EMAIL_USE_TLS = True   # USE_TLS and USE_SSL are mutually exclusive,
EMAIL_USE_SSL = False  # see https://docs.djangoproject.com/en/3.0/ref/settings/#email-use-tls

# The ADMINS setting is needed when the AdminEmailHandler is used
# https://docs.djangoproject.com/en/3.0/topics/logging/#django.utils.log.AdminEmailHandler
ADMINS = [('Anne', 'anne@cleansys.headquarters')]

# If you want to test the AdminEmailHandler without an email-server, uncomment these lines.
# Don't forget to comment them back out again
# https://docs.djangoproject.com/en/3.0/topics/email/#file-backend
# EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
# EMAIL_FILE_PATH = '/logs/emails'

# Logging settings
LOGGING['LOG_SCHEDULE_CREATE_ASSIGNMENT_TO_FILE'] = False

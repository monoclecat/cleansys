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

# Logging settings
LOGGING['LOG_SCHEDULE_CREATE_ASSIGNMENT_TO_FILE'] = False

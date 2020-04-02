# Copy settings_templates/ directory and paste it into the same parent directory under the name 'settings'.
# The folder 'settings' is already mentioned in .gitignore
# This procedure prevents updates from screwing up your settings!
#
# /root-directory
#   /cleansys
#       /settings_templates
#           /__init__.py
#           /common_settings.py
#           /dev_settings.py
#       /settings
#           /__init__.py
#           /common_settings.py
#           /dev_settings.py
#   /webinterface
#       / ...
#
# Then, the following import statement will work.

from .common_settings import *  # Common settings - always needed

from .dev_settings import *  # Settings for local development and testing
# from .prod_settings import *  # Settings for deployment (= "production")

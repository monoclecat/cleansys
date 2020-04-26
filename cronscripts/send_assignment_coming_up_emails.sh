#! /bin/bash

cd /var/www/cleansys/ || (echo "Changing directory to /var/www/cleansys failed!"; exit)
source bin/activate || (echo "Activating virtualenv in /var/www/cleansys/bin/activate failed!"; exit)

python3 manage.py send_assignment_coming_up_emails
echo "$(date): python3 manage.py send_assignment_coming_up_emails was run."

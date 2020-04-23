#! /bin/bash

cd /var/www/cleansys/ || (echo "Changing directory to /var/www/cleansys failed!"; exit)

test -d backups || (mkdir backups; echo "$(date): Created directory backups")

backup_file_path=backups/db_sqlite3__"$(date +"%Y_%m_%d__%H_%M")".gz
(test -f "$backup_file_path" && echo "$(date): Database backup already exists.") || (gzip -k db.sqlite3 > "$backup_file_path"; echo "$(date): Database backed up!")
test -f "db.sqlite3.gz" && test -f "$backup_file_path" && rm "db.sqlite3.gz"

"""ihaCDN File Cleaner.
This will remove any file exceeding the maximum age.

Code are based on: https://github.com/mia-0/0x0/blob/master/cleanup.py
"""

from app import app
import os
import time
import datetime

# Settings.
max_days = app.config.FILE_RETENTION_MAX_AGE
min_days = app.config.FILE_RETENTION_MIN_AGE
filesize_limit = app.config.FILESIZE_LIMIT

if not app.config.ENABLE_FILE_RETENTION:
    exit(0)

calculate_retention = (
    lambda fsz: min_days + (-max_days + min_days) * (fsz / filesize_limit - 1) ** 5
)  # noqa: E501,E731

os.chdir(app.config.UPLOAD_PATH)

files = [f for f in os.listdir(".")]


for f in files:
    stat = os.stat(f)
    systime = time.time()
    file_age = datetime.timedelta(seconds=systime - stat.st_mtime).days
    max_age = calculate_retention(stat.st_size)

    if file_age >= max_age:
        os.remove(f)

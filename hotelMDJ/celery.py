"""Celery application of the Hotel MDJ project.

Redis is the message broker: Django publishes tasks there and the
``celery_worker`` container consumes them in the background. Settings are read
from ``hotelMDJ/settings.py`` under the ``CELERY_`` prefix.

Run a worker locally with:

    celery -A hotelMDJ worker -l info --pool=solo     (``--pool=solo`` on Windows)
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hotelMDJ.settings")

app = Celery("hotelMDJ")
app.config_from_object("django.conf:settings", namespace="CELERY")

# Finds ``tasks.py`` in every installed app (reservation/tasks.py).
app.autodiscover_tasks()

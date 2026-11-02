import time

from django.core.management.base import BaseCommand

from clinic import notify
from clinic.models import Notification


class Command(BaseCommand):
    def add_arguments(self, p):
        p.add_argument("--loop", action="store_true")

    def handle(self, *a, **o):
        while True:
            for n in Notification.objects.filter(status="pending").order_by("id")[:50]:
                notify.deliver(n)
            if not o["loop"]:
                return
            time.sleep(5)

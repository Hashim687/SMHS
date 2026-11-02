from django.apps import AppConfig


class ClinicConfig(AppConfig):
    name = "clinic"

    def ready(self):
        from django.db.models.signals import post_delete, post_save

        from . import triage
        from .models import Symptom, TriageRule

        for m in (Symptom, TriageRule):
            post_save.connect(lambda **k: triage.invalidate(), sender=m, weak=False)
            post_delete.connect(lambda **k: triage.invalidate(), sender=m, weak=False)

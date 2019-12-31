from django.apps import AppConfig
from django.db.utils import OperationalError


class MyAppConfig(AppConfig):
    name = "chat"

    def ready(self):
        from .models import Doctor, PatientQueue

        try:
            Doctor.objects.filter(status="ACTIVE").update(status="SERVER_DC")
            Doctor.objects.filter(status="WAIT").update(status="SERVER_DC")
            PatientQueue.objects.filter(status="ACTIVE").update(status="SERVER_DC")
            PatientQueue.objects.filter(status="WAIT").update(status="SERVER_DC")
        except OperationalError:
            pass

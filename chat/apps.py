from django.apps import AppConfig
from django.db.utils import OperationalError

class MyAppConfig(AppConfig):
    name = 'chat'

    def ready(self):
        from .models import Doctor, PatientQueue


        # TODO also change wait
        try:
            a = Doctor.objects.filter(status="ACTIVE").update(status="SERVER_DC")
            b = PatientQueue.objects.filter(status="ACTIVE").update(status="SERVER_DC")
        except OperationalError:
            pass
        else:
            for i in (a,b):
                if i:
                    print(i)

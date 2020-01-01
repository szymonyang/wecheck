from django.contrib import admin
from .models import Doctor, PatientQueue


admin.site.register(Doctor)
admin.site.register(PatientQueue)

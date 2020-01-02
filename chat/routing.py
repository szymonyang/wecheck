from django.urls import re_path

from .doctor import DoctorConsumer
from .patient import PatientConsumer

websocket_urlpatterns = [
    re_path(r'ws/patient', PatientConsumer),
    re_path(r'ws/doctor', DoctorConsumer),
]

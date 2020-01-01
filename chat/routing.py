from django.urls import re_path

from .patient import PatientConsumer
from .doctor import DoctorConsumer

websocket_urlpatterns = [
    re_path(r'ws/patient', PatientConsumer),
    re_path(r'ws/doctor', DoctorConsumer),
]

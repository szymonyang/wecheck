from django.urls import path

from . import views

urlpatterns = [
    path('patient', views.patient, name='patient'),
    path('doctor', views.doctor, name='doctor'),
]

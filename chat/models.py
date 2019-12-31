from django.db import models

STATES = [(i, i.capitalize()) for i in ("QUEUE", "RESERVE", "CHAT")]
STATUS = [(i, i.capitalize()) for i in ("ACTIVE", "SERVER_DC", "USER_DC", "WAIT", "COMPLETE")]


class PatientQueue(models.Model):
    browser = models.CharField(max_length=100, unique=True)
    channel = models.CharField(max_length=100, unique=True)
    state = models.CharField(max_length=10, choices=STATES, default="QUEUE")
    status = models.CharField(max_length=10, choices=STATES, default="ACTIVE")


class Doctor(models.Model):
    browser = models.CharField(max_length=100, unique=True)
    channel = models.CharField(max_length=100, unique=True)
    patient = models.ForeignKey(PatientQueue, null=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=10, choices=STATES, default="ACTIVE")

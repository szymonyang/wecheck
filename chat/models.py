from django.db import models


class Patient(models.Model):
    channel = models.CharField(max_length=100, unique=True)
    status = models.TextChoices('queue', 'chatting')


class Doctor(models.Model):
    channel = models.CharField(max_length=100, unique=True)
    patient = models.ForeignKey(Patient, null=True, on_delete=models.SET_NULL)

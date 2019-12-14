from django.shortcuts import render
from django.utils.safestring import mark_safe
import json

def doctor(request):
    return render(request, 'chat/doctor.html', {})

def patient(request):
    return render(request, 'chat/patient.html', {})

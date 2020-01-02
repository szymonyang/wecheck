from django.shortcuts import render


def doctor(request):
    return render(request, 'chat/doctor.html', {})

def patient(request):
    return render(request, 'chat/patient.html', {})

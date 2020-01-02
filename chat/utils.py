from urllib.parse import parse_qs
from asgiref.sync import async_to_sync

from .models import Doctor, PatientQueue


def queue_message(num):
    if num > 1:
        return f"There are {num} people ahead in the queue."
    elif num == 1:
        return "There is one person ahead in the queue."
    return "You are at the front of the queue."


def get_browser(query_string):
    return parse_qs(query_string)[b"browser"][0]


def get_queue():
    return [i.id for i in PatientQueue.objects.filter(state="QUEUED", status="ACTIVE")]


def queue_update_patients(channel_layer):
    for num, patient in enumerate(PatientQueue.objects.filter(state="QUEUED", status="ACTIVE").order_by("id")):
        async_to_sync(channel_layer.send)(
            patient.channel, {"type": "send_json", "action": "queue", "message": queue_message(num)}
        )


def queue_update_doctors(channel_layer):
    queue = get_queue()
    for doctor in Doctor.objects.filter(patient=None):
        async_to_sync(channel_layer.send)(doctor.channel, {"type": "send_json", "action": "queue", "message": queue})

from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer

from .models import Doctor, PatientQueue
from .utils import print_message, queue_update_doctors, queue_update_patients, get_browser


def queue_message(num):
    if num > 1:
        return f"There are {num} people ahead in the queue."
    elif num == 1:
        return "There is one person ahead in the queue."
    return "You are at the front of the queue."


class PatientConsumer(JsonWebsocketConsumer):
    def send_json(self, content):
        print_message(self.scope["client"][0], self.channel_name, "received", content)
        super().send_json(content)

    def connect(self):
        PatientQueue.objects.create(channel=self.channel_name, status="queue")
        self.accept()
        # Add patient to the end of the queue
        queue_length = PatientQueue.objects.filter(status="queue").count()
        self.send_json({"action": "queue", "message": queue_message(queue_length - 1)})
        queue_update_doctors(self.channel_layer)

    def disconnect(self, close_code):
        patient = PatientQueue.objects.get(channel=self.channel_name)
        if patient.status == "chatting":
            doctor = Doctor.objects.filter(patient=patient)[0]
            async_to_sync(self.channel_layer.send)(doctor.channel, {"type": "send_json", "action": "patient_left"})
        patient.delete()  # This sets null for the doctor
        queue_update_patients(self.channel_layer)
        queue_update_doctors(self.channel_layer)

    def receive_json(self, content):
        print_message(self.scope["client"][0], self.channel_name, "sent", content)
        action = content.get("action")
        if action == "chat":
            patient = PatientQueue.objects.get(channel=self.channel_name)
            if patient.status == "chatting":
                doctor = Doctor.objects.get(patient=patient)
                async_to_sync(self.channel_layer.send)(
                    doctor.channel, {"type": "send_json", "action": "chat", "message": f"Patient: {content['message']}"}
                )
                self.send_json({"action": "chat", "message": f"You   : {content['message']}"})

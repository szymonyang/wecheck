from channels.generic.websocket import JsonWebsocketConsumer
from .models import Doctor, Patient


def get_queue():
    return [i.id for i in Patient.objects.filter(status="queue")]


class PatientConsumer(JsonWebsocketConsumer):
    def connect(self):
        Patient.objects.create(channel=self.channel_name, status="queue")
        self.accept()
        # self.send_json({"message": "Hello patient"})

    def disconnect(self, close_code):
        pass

    def receive_json(self, content):
        print(f"{self.channel_name} received data {content}")


class DoctorConsumer(JsonWebsocketConsumer):
    def connect(self):
        Doctor.objects.create(channel=self.channel_name)
        self.accept()
        self.send_json({"type": "queue", "queue": get_queue()})

    def disconnect(self, close_code):
        pass

    def receive_json(self, content):
        print(f"{self.channel_name} received data {content}")

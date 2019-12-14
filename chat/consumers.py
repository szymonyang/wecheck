from channels.generic.websocket import JsonWebsocketConsumer
from .models import Doctor, Patient
from asgiref.sync import async_to_sync


def get_queue():
    return [i.id for i in Patient.objects.filter(status="queue")]


class PatientConsumer(JsonWebsocketConsumer):
    def connect(self):
        Patient.objects.create(channel=self.channel_name, status="queue")
        self.accept()

    def disconnect(self, close_code):
        Patient.objects.get(channel=self.channel_name).delete()
        # TODO:Update queue state for all doctors

    def receive_json(self, content):
        print(f"{self.channel_name} received data {content}")


class DoctorConsumer(JsonWebsocketConsumer):
    def connect(self):
        Doctor.objects.create(channel=self.channel_name)
        self.accept()
        self.send_json({"type": "queue", "queue": get_queue()})

    def disconnect(self, close_code):
        Doctor.objects.get(channel=self.channel_name).delete()

    def receive_json(self, content):
        print(f"{self.channel_name} received data {content}")
        if content['type'] == 'connect':
            # Update model state
            patient = Patient.objects.get(id=content['destination'])
            patient.status = "chatting"
            patient.save()

            doctor = Doctor.objects.get(channel=self.channel_name)
            doctor.patient = patient
            doctor.save()

            # TODO:Update queue state for all doctors

            # Update patient
            async_to_sync(self.channel_layer.send)(patient.channel, {'type': 'start'})
            async_to_sync(self.channel_layer.send)(patient.channel, {'message': 'Now chatting with a doctor'})

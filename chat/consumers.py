from channels.generic.websocket import JsonWebsocketConsumer
from .models import Doctor, Patient
from asgiref.sync import async_to_sync


def get_queue():
    return [i.channel for i in Patient.objects.filter(status="queue")]


class PatientConsumer(JsonWebsocketConsumer):
    def connect(self):
        Patient.objects.create(channel=self.channel_name, status="queue")
        self.accept()

    def disconnect(self, close_code):
        Patient.objects.get(channel=self.channel_name).delete()
        # TODO:Update queue state for all doctors

    def receive_json(self, content):
        print(f"{self.channel_name} received data {content}")
        self.send_json(content)


class DoctorConsumer(JsonWebsocketConsumer):
    def connect(self):
        Doctor.objects.create(channel=self.channel_name)
        self.accept()
        queue = get_queue()
        print(queue)
        self.send_json({"action": "queue", "queue": queue})

    def disconnect(self, close_code):
        Doctor.objects.get(channel=self.channel_name).delete()

    def receive_json(self, content):
        print(f"{self.channel_name} received data {content}")
        if content.get('action') == 'connect':
            # Update model state
            patient = Patient.objects.get(channel=content['destination'])
            patient.status = "chatting"
            patient.save()

            doctor = Doctor.objects.get(channel=self.channel_name)
            doctor.patient = patient
            doctor.save()

            # TODO:Update queue state for all doctors

            async_to_sync(self.channel_layer.send)(doctor.channel, {"type": "send_json", 'message': 'Now chatting with the patient'})

            # Update patient
            async_to_sync(self.channel_layer.send)(patient.channel, {"type": "send_json", 'action': 'start'})
            async_to_sync(self.channel_layer.send)(patient.channel, {"type": "send_json", 'message': 'Now chatting with a doctor'})

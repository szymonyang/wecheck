import logging
from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer

from .models import Doctor, PatientQueue
from .utils import get_browser, get_queue, queue_update_patients, queue_update_doctors

logger = logging.getLogger(__name__)


class DoctorConsumer(JsonWebsocketConsumer):
    def send_json(self, content):
        print(f"{self.scope['client'][0]}, {self.channel_name}, received, {content}")
        super().send_json(content)

    def connect(self):
        browser = get_browser(self.scope["query_string"])
        doctor, created = Doctor.objects.update_or_create(browser=browser, defaults={"channel": self.channel_name})
        self.accept()

        print(f"Doctor {'' if created else 're'}joined")
        if not doctor.patient:
            if doctor.status != "ACTIVE":
                doctor.status = "ACTIVE"
                doctor.save()
            self.send_json({"action": "queue", "message": get_queue()})
        else:
            patient = doctor.patient
            if patient.status == "WAIT":
                patient.status = "ACTIVE"
                patient.save()
                doctor.status = "ACTIVE"
                doctor.save()
                if patient.state == "RESERVED":
                    self.send_json({"action": "reserve"})
                    self.message(patient, {"action": "reserve"})
                elif patient.state == "CHAT":
                    self.send_json({"action": "start_chat"})
                    self.message(patient, {"action": "start_chat"})
            else:
                doctor.status = "WAIT"
                doctor.save()
                self.send_json({"action": "wait"})

    def disconnect(self, close_code):
        doctor = Doctor.objects.get(channel=self.channel_name)
        doctor.status = "USER_DC"
        doctor.save()

        if doctor.patient:
            patient = doctor.patient
            patient.status = "WAIT"
            patient.save()
            self.message(doctor.patient, {"action": "wait"})

    def receive_json(self, content):
        print(f"{self.scope['client'][0]}, {self.channel_name}, sent, {content}")

        action = content.get("action")
        if action == "reserve":
            self.reserve(content["message"])
        elif action == "unreserve":
            self.unreserve()
        elif action == "start_chat":
            self.start_chat()
        elif action == "chat":
            self.chat(content["message"])
        elif action == "end_chat":
            self.end_chat()
        elif action == "wait_timeout":
            self.wait_timeout()

    def message(self, patient, message):
        message["type"] = "send_json"
        async_to_sync(self.channel_layer.send)(patient.channel, message)

    def reserve(self, user_id):
        patient = PatientQueue.objects.get(id=user_id)
        patient.state = "RESERVED"
        patient.save()
        doctor = Doctor.objects.get(channel=self.channel_name)
        doctor.patient = patient
        doctor.save()
        self.send_json({"action": "cdss", "message": f"CDSS patient {patient.id} content here"})
        self.message(patient, {"action": "reserve"})
        queue_update_patients(self.channel_layer)
        queue_update_doctors(self.channel_layer)

    def unreserve(self):
        doctor = Doctor.objects.get(channel=self.channel_name)
        doctor.patient.state = "QUEUED"
        doctor.patient.save()
        doctor.patient = None
        doctor.save()
        queue_update_patients(self.channel_layer)
        queue_update_doctors(self.channel_layer)

    def start_chat(self):
        doctor = Doctor.objects.get(channel=self.channel_name)
        doctor.patient.state = "CHAT"
        doctor.patient.save()

        self.send_json({"action": "chat", "message": "You are now chatting with the patient"})
        self.message(doctor.patient, {"action": "start_chat"})
        self.message(doctor.patient, {"action": "chat", "message": "You are now chatting with a doctor"})

    def chat(self, message):
        doctor = Doctor.objects.get(channel=self.channel_name)
        self.message(doctor.patient, {"action": "chat", "message": f"Doctor: {message}"})
        self.send_json({"action": "chat", "message": f"You    : {message}"})

    def end_chat(self):
        doctor = Doctor.objects.get(channel=self.channel_name)
        self.message(doctor.patient, {"action": "end_chat"})
        doctor.patient.delete()
        self.send_json({"action": "queue", "message": get_queue()})

    def wait_timeout(self):
        doctor = Doctor.objects.get(channel=self.channel_name)
        if doctor.patient:
            doctor.patient.state = "QUEUED"
            doctor.patient.save()
            doctor.patient = None
        doctor.state = "QUEUED"
        doctor.status = "ACTIVE"
        doctor.save()
        self.send_json({"action": "queue", "message": get_queue()})

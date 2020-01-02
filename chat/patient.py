from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer

from .models import Doctor, PatientQueue
from .utils import queue_update_doctors, queue_update_patients, get_browser, queue_message


class PatientConsumer(JsonWebsocketConsumer):
    def send_json(self, content):
        print(f"{self.scope['client'][0]}, {self.channel_name}, received, {content}")
        super().send_json(content)

    def connect(self):
        browser = get_browser(self.scope["query_string"])
        patient, created = PatientQueue.objects.update_or_create(
            browser=browser, defaults={"channel": self.channel_name}
        )
        self.accept()
        print(f"Patient {'' if created else 're'}joined")

        if patient.state == "QUEUED":
            if patient.status != "ACTIVE":
                patient.status = "ACTIVE"
                patient.save()
            queue_update_patients(self.channel_layer)
            queue_update_doctors(self.channel_layer)
        else:
            # Patient is trying to rejoin with their doctor
            doctor = Doctor.objects.get(patient=patient)
            if doctor.status == "WAIT":
                doctor.status = "ACTIVE"
                doctor.save()
                patient.status = "ACTIVE"
                patient.save()
                if patient.state == "RESERVED":
                    self.send_json({"action": "reserve"})
                    self.message(doctor, {"action": "reserve"})
                elif patient.state == "CHAT":
                    self.send_json({"action": "start_chat"})
                    self.message(doctor, {"action": "start_chat"})
            else:
                patient.status = "WAIT"
                patient.save()
                self.send_json({"action": "wait"})

    def disconnect(self, close_code):
        patient = PatientQueue.objects.get(channel=self.channel_name)
        patient.status = "USER_DC"
        patient.save()

        if patient.state in ("CHAT", "RESERVED"):
            doctor = Doctor.objects.get(patient=patient)
            doctor.status = "WAIT"
            doctor.save()
            self.message(doctor, {"action": "wait"})
        else:
            queue_update_patients(self.channel_layer)
            queue_update_doctors(self.channel_layer)

    def receive_json(self, content):
        print(f"{self.scope['client'][0]}, {self.channel_name}, sent, {content}")
        action = content.get("action")
        if action == "chat":
            self.chat(content["message"])
        elif action == "wait_timeout":
            self.wait_timeout()

    def message(self, doctor, message):
        message["type"] = "send_json"
        async_to_sync(self.channel_layer.send)(doctor.channel, message)

    def chat(self, message):
        patient = PatientQueue.objects.get(channel=self.channel_name)
        if patient.state == "CHAT":
            doctor = Doctor.objects.get(patient=patient)
            self.message(doctor, {"action": "chat", "message": f"Patient: {message}"})
            self.send_json({"action": "chat", "message": f"You   : {message}"})

    def wait_timeout(self):
        patient = PatientQueue.objects.get(channel=self.channel_name)
        patient.state = "QUEUED"
        patient.status = "ACTIVE"
        patient.save()
        doctor = Doctor.objects.get(patient=patient)
        doctor.patient = None
        doctor.save()
        queue_update_patients(self.channel_layer)
        queue_update_doctors(self.channel_layer)

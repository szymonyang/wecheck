from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer

from .models import Doctor, PatientQueue
from .utils import print_message, queue_update_doctors, queue_update_patients, get_browser, queue_message


class PatientConsumer(JsonWebsocketConsumer):
    def send_json(self, content):
        print_message(self.scope["client"][0], self.channel_name, "received", content)
        super().send_json(content)

    def connect(self):
        browser = get_browser(self.scope['query_string'])
        patient, _ = PatientQueue.objects.update_or_create(browser=browser, defaults={"channel": self.channel_name})
        self.accept()

        if patient.state == "QUEUED":
            if patient.status != "ACTIVE":
                patient.status = "ACTIVE"
                patient.save()
            queue_update_patients(self.channel_layer)
            queue_update_doctors(self.channel_layer)
        else:
            # Patient is trying to rejoin with their doctor
            assigned_doctor = Doctor.objects.get(patient=patient)
            if assigned_doctor.status == "WAIT":
                assigned_doctor.status = "ACTIVE"
                assigned_doctor.save()
                patient.status = "ACTIVE"
                patient.save()
                if patient.state == "RESERVED":
                    self.send_json({"action": "reserve"})
                elif patient.state == "CHAT":
                    self.send_json({"action": "start_chat"})
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
            async_to_sync(self.channel_layer.send)(doctor.channel, {"type": "send_json", "action": "wait"})
        else:
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
        elif action == "wait_timeout":
            # The patient was waiting for a doctor, but this doctor has not returned
            patient = PatientQueue.objects.get(channel=self.channel_name)
            patient.state="QUEUED"
            patient.status="ACTIVE"
            patient.save()
            doctor = Doctor.objects.get(patient=patient)
            doctor.patient=None
            doctor.save()
            queue_update_patients(self.channel_layer)
            queue_update_doctors(self.channel_layer)

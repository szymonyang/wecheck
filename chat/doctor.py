from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer

from .models import Doctor, PatientQueue
from .utils import get_browser, get_queue, print_message, queue_update_patients, queue_update_doctors


class DoctorConsumer(JsonWebsocketConsumer):
    def send_json(self, content):
        print_message(self.scope["client"][0], self.channel_name, "received", content)
        super().send_json(content)

    def connect(self):
        browser = get_browser(self.scope["query_string"])
        doctor, _ = Doctor.objects.update_or_create(browser=browser, defaults={"channel": self.channel_name})
        self.accept()

        if doctor.state == "QUEUED":
            if doctor.status != "ACTIVE":
                doctor.status = "ACTIVE"
                doctor.save()
            self.send_json({"action": "queue", "message": get_queue()})
        else:
            assigned_patient = doctor.patient
            if assigned_patient.status == "WAIT":
                assigned_patient.status = "ACTIVE"
                assigned_patient.save()
                doctor.status = "ACTIVE"
                doctor.save()
                if patient.state == "RESERVED":
                    self.send_json({"action": "reserve"})
                    async_to_sync(self.channel_layer.send)(patient.channel, {"type": "send_json", "action": "reserve"})
                elif patient.state == "CHAT":
                    self.send_json({"action": "start_chat"})
                    async_to_sync(self.channel_layer.send)(
                        patient.channel, {"type": "send_json", "action": "start_chat"}
                    )
            else:
                doctor.status = "WAIT"
                doctor.save
                self.send_json({"action": "wait"})

    def disconnect(self, close_code):
        doctor = Doctor.objects.get(channel=self.channel_name)
        if doctor.patient:
            async_to_sync(self.channel_layer.send)(
                doctor.patient.channel,
                {"type": "send_json", "action": "doctor_left", "message": "The doctor left the chat. Exiting."},
            )
        doctor.delete()

    def receive_json(self, content):
        print_message(self.scope["client"][0], self.channel_name, "sent", content)
        action = content.get("action")
        if action == "reserve":
            patient = PatientQueue.objects.get(id=content["message"])
            patient.state = "RESERVED"
            patient.save()
            doctor = Doctor.objects.get(channel=self.channel_name)
            doctor.patient = patient
            doctor.save()
            self.send_json({"action": "cdss", "message": f"CDSS patient {patient.id} content here"})
            async_to_sync(self.channel_layer.send)(patient.channel, {"type": "send_json", "action": "reserve"})
            queue_update_patients(self.channel_layer)
            queue_update_doctors(self.channel_layer)
        elif action == "start_chat":
            # Update model state
            doctor = Doctor.objects.get(channel=self.channel_name)
            doctor.patient.status = "chatting"
            doctor.patient.save()

            self.send_json({"action": "chat", "message": "You are now chatting with the patient"})
            # Update patient
            async_to_sync(self.channel_layer.send)(
                doctor.patient.channel, {"type": "send_json", "action": "start_chat"}
            )
            async_to_sync(self.channel_layer.send)(
                doctor.patient.channel,
                {"type": "send_json", "action": "chat", "message": "You are now chatting with a doctor"},
            )
        elif action == "chat":
            doctor = Doctor.objects.get(channel=self.channel_name)
            async_to_sync(self.channel_layer.send)(
                doctor.patient.channel,
                {"type": "send_json", "action": "chat", "message": f"Doctor: {content['message']}"},
            )
            self.send_json({"action": "chat", "message": f"You    : {content['message']}"})
        elif action == "unreserve":
            doctor = Doctor.objects.get(channel=self.channel_name)
            doctor.patient.status = "queue"
            doctor.patient.save()
            doctor.patient = None
            doctor.save()
            queue_update_patients(self.channel_layer)
            queue_update_doctors(self.channel_layer)
        elif action == "end_chat":
            doctor = Doctor.objects.get(channel=self.channel_name)
            async_to_sync(self.channel_layer.send)(doctor.patient.channel, {"type": "send_json", "action": "end_chat"})
            doctor.patient.delete()
            self.send_json({"action": "queue", "message": get_queue()})

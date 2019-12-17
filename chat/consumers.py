from channels.generic.websocket import JsonWebsocketConsumer
from .models import Doctor, Patient
from asgiref.sync import async_to_sync


def get_queue():
    return [i.channel for i in Patient.objects.filter(status="queue")]


def queue_message(num):
    if num > 1:
        return f"There are {num-1} people ahead in the queue."
    elif num == 1:
        return "There is one person ahead in the queue."
    return "You are at the front of the queue."


def queue_update_patients(channel_layer):
    for num, patient in enumerate(Patient.objects.filter(status="queue").order_by("id")):
        async_to_sync(channel_layer.send)(
            patient.channel, {"type": "send_json", "action": "queue", "message": queue_message(num)}
        )


def queue_update_doctors(channel_layer):
    queue = get_queue()
    for doctor in Doctor.objects.filter(patient=None):
        async_to_sync(channel_layer.send)(doctor.channel, {"type": "send_json", "action": "queue", "message": queue})


class PatientConsumer(JsonWebsocketConsumer):
    def send_json(self, content):
        print(f"{self.channel_name} sending {content}")
        super().send_json(content)

    def connect(self):
        Patient.objects.create(channel=self.channel_name, status="queue")
        self.accept()
        # Add patient to the end of the queue
        queue_length = Patient.objects.filter(status="queue").count()
        self.send_json({"action": "queue", "message": queue_message(queue_length - 1)})
        queue_update_doctors(self.channel_layer)

    def disconnect(self, close_code):
        patient = Patient.objects.get(channel=self.channel_name)
        if patient.status == "chatting":
            doctor = Doctor.objects.filter(patient=patient)[0]
            async_to_sync(self.channel_layer.send)(doctor.channel, {"type": "send_json", "action": "patient_left"})
        patient.delete()  # This sets null for the doctor
        queue_update_patients(self.channel_layer)
        queue_update_doctors(self.channel_layer)

    def receive_json(self, content):
        print(f"{self.channel_name} received data {content}")
        action = content.get("action")
        if action == "chat":
            patient = Patient.objects.get(channel=self.channel_name)
            if patient.status == "chatting":
                doctor = Doctor.objects.get(patient=patient)
                async_to_sync(self.channel_layer.send)(
                    doctor.channel, {"type": "send_json", "message": content["message"]}
                )
                self.send_json({"action": "chat", "message": content["message"]})


class DoctorConsumer(JsonWebsocketConsumer):
    def send_json(self, content):
        print(f"{self.channel_name} sending {content}")
        super().send_json(content)

    def connect(self):
        Doctor.objects.create(channel=self.channel_name)
        self.accept()
        self.send_json({"action": "queue", "message": get_queue()})

    def disconnect(self, close_code):
        doctor = Doctor.objects.get(channel=self.channel_name)
        if doctor.patient:
            async_to_sync(self.channel_layer.send)(
                doctor.patient.channel,
                {"type": "send_json", "action": "doctor_left", "message": "The doctor left the chat. Exiting."},
            )
        doctor.delete()

    def receive_json(self, content):
        print(f"{self.channel_name} received data {content}")
        action = content.get("action")
        if action == "reserve":
            patient = Patient.objects.get(channel=content["message"])
            patient.status = "reserved"
            patient.save()
            doctor = Doctor.objects.get(channel=self.channel_name)
            doctor.patient = patient
            doctor.save()
            self.send_json({"action": "cdss", "message": "CDSS patient content here"})
            async_to_sync(self.channel_layer.send)(patient.channel, {"type": "send_json", "action": "reserve"})
            queue_update_patients(self.channel_layer)
            queue_update_doctors(self.channel_layer)
        elif action == "start_chat":
            # Update model state
            doctor = Doctor.objects.get(channel=self.channel_name)
            doctor.patient.status = "chatting"
            doctor.patient.save()

            self.send_json({"action": "chat", "message": "Now chatting with the patient"})
            # Update patient
            async_to_sync(self.channel_layer.send)(patient.channel, {"type": "send_json", "action": "start_chat"})
            async_to_sync(self.channel_layer.send)(
                patient.channel, {"type": "send_json", "action": "chat", "message": "Now chatting with a doctor"}
            )
        elif action == "chat":
            doctor = Doctor.objects.get(channel=self.channel_name)
            async_to_sync(self.channel_layer.send)(
                doctor.patient.channel, {"type": "send_json", "action": "chat", "message": content["message"]}
            )
            self.send_json({"action": "chat", "message": content["message"]})
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
            doctor.patient.delete()
            self.send_json({"action": "queue", "message": get_queue()})

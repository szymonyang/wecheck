from typing import Any, Dict

from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer

from .models import Doctor, PatientQueue
from .utils import (get_browser, get_queue, queue_update_doctors,
                    queue_update_patients)


class DoctorConsumer(JsonWebsocketConsumer):
    def send_json(self, content: Dict[str, Any]):
        """For logging"""

        print(f"{self.scope['client'][0]}, {self.channel_name}, received, {content}")
        super().send_json(content)

    def connect(self):
        """Deal with client trying to make new websocket connection

        1. Get browser tab id
        2. Find Doctor in database (or create if new doctor)
        3. Accept the websocket connection.
        4. If the doctor doesn't have a patient then they are in the queue. Mark them active and show them the queue.
        5. Otherwise the doctor is paired with a patient.
        6. If the patient is already waiting for them then reconnect the doctor and the patient.
        7. Otherwise the patient is not connected, so tell the doctor to wait for their patient.
        """

        browser = get_browser(self.scope["query_string"])
        doctor, created = Doctor.objects.update_or_create(browser=browser, defaults={"channel": self.channel_name})
        self.accept()

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
        """Deal with client disconnect

        1. Update the state of the doctor in the databse.
        2. If the doctor was connected with a patient then tell the patient to wait for the doctor.
        """

        doctor = Doctor.objects.get(channel=self.channel_name)
        doctor.status = "USER_DC"
        doctor.save()

        if doctor.patient:
            patient = doctor.patient
            patient.status = "WAIT"
            patient.save()
            self.message(doctor.patient, {"action": "wait"})

    def receive_json(self, content: Dict[str, Any]):
        """
        Receive a message and process the triggered action.
        The messages recieved by this method come from the doctor client.

        Parameters
        ----------
        content
            JSON structured dictionary. Should always have a key "action".
        """

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

    def message(self, patient, content: Dict[str, Any]):
        """Send a message to the patient

        Parameters
        ----------
        content
            The action and other data to send to the patient.
        """

        content["type"] = "send_json"
        async_to_sync(self.channel_layer.send)(patient.channel, content)

    def reserve(self, user_id: str):
        """The doctor has selected a patient out of the queue and reserved them."""

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
        """Return patient reserved by the doctor back to the queue."""

        doctor = Doctor.objects.get(channel=self.channel_name)
        doctor.patient.state = "QUEUED"
        doctor.patient.save()
        doctor.patient = None
        doctor.save()
        queue_update_patients(self.channel_layer)
        queue_update_doctors(self.channel_layer)

    def start_chat(self):
        """Begin chatting with the patient who is currently reserved."""

        doctor = Doctor.objects.get(channel=self.channel_name)
        doctor.patient.state = "CHAT"
        doctor.patient.save()

        self.send_json({"action": "chat", "message": "You are now chatting with the patient"})
        self.message(doctor.patient, {"action": "start_chat"})
        self.message(doctor.patient, {"action": "chat", "message": "You are now chatting with a doctor"})

    def chat(self, message: str):
        """Send a text message to the patient."""

        doctor = Doctor.objects.get(channel=self.channel_name)
        self.message(doctor.patient, {"action": "chat", "message": f"Doctor: {message}"})
        self.send_json({"action": "chat", "message": f"You    : {message}"})

    def end_chat(self):
        """End the chat with the patient."""

        doctor = Doctor.objects.get(channel=self.channel_name)
        self.message(doctor.patient, {"action": "end_chat"})
        doctor.patient.status = "COMPLETE"
        doctor.patient.save()
        doctor.patient = None
        doctor.save()
        self.send_json({"action": "queue", "message": get_queue()})

    def wait_timeout(self):
        """The doctor is finished waiting for the patient and stops waiting for the patient."""

        doctor = Doctor.objects.get(channel=self.channel_name)
        if doctor.patient:
            doctor.patient.state = "QUEUED"
            doctor.patient.save()
            doctor.patient = None
        doctor.state = "QUEUED"
        doctor.status = "ACTIVE"
        doctor.save()
        self.send_json({"action": "queue", "message": get_queue()})

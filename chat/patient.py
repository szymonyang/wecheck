from typing import Any, Dict

from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer

from .models import Doctor, PatientQueue
from .utils import (get_browser, queue_message, queue_update_doctors,
                    queue_update_patients)


class PatientConsumer(JsonWebsocketConsumer):
    def send_json(self, content: Dict[str, Any]):
        """For logging"""

        print(f"{self.scope['client'][0]}, {self.channel_name}, received, {content}")
        super().send_json(content)

    def connect(self):
        """Deal with client trying to make new websocket connection

        1. Get browser tab id
        2. Find patient in database (or create if new patient)
        3. Accept the websocket connection.
        4. If the patient is in the state "QUEUED" (which is the default state for new patients) add them to the queue.
        5. Otherwise the patient is paired with a doctor.
        6. If the doctor is waiting for the patient then reconnect them.
        7. Otherwise the doctor is not connected, so tell the patient to wait for their doctor.
        """

        browser = get_browser(self.scope["query_string"])
        patient, created = PatientQueue.objects.update_or_create(
            browser=browser, defaults={"channel": self.channel_name}
        )
        self.accept()

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
        """Deal with client disconnect

        1. Update the state of the patient in the databse.
        2. If the doctor was connected with a patient then tell the patient to wait for the doctor.
        3. Otherwise update the queue because a patient just left the queue.
        """

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

    def receive_json(self, content: Dict[str, Any]):
        """
        Receive a message and process the triggered action.
        The messages recieved by this method come from the patient client.

        Parameters
        ----------
        content
            JSON structured dictionary. Should always have a key "action".
        """

        print(f"{self.scope['client'][0]}, {self.channel_name}, sent, {content}")
        action = content.get("action")
        if action == "chat":
            self.chat(content["message"])
        elif action == "wait_timeout":
            self.wait_timeout()

    def message(self, doctor, content: Dict[str, Any]):
        """Send a message to the doctor

        Parameters
        ----------
        doctor
            Django ORM object with a field .channel which is a string representing channel_name

        content
            The action and other data to send to the patient.
        """

        content["type"] = "send_json"
        async_to_sync(self.channel_layer.send)(doctor.channel, content)

    def chat(self, message: str):
        """Send a text message to the doctor."""

        patient = PatientQueue.objects.get(channel=self.channel_name)
        if patient.state == "CHAT":
            doctor = Doctor.objects.get(patient=patient)
            self.message(doctor, {"action": "chat", "message": f"Patient: {message}"})
            self.send_json({"action": "chat", "message": f"You   : {message}"})

    def wait_timeout(self):
        """The patient is finished waiting for the doctor and stops waiting for the doctor."""

        patient = PatientQueue.objects.get(channel=self.channel_name)
        patient.state = "QUEUED"
        patient.status = "ACTIVE"
        patient.save()
        doctor = Doctor.objects.get(patient=patient)
        doctor.patient = None
        doctor.save()
        queue_update_patients(self.channel_layer)
        queue_update_doctors(self.channel_layer)

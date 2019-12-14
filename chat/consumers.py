from channels.generic.websocket import JsonWebsocketConsumer


class PatientConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.accept()
        self.send_json({"message": "Hello patient"})

    def disconnect(self, close_code):
        pass

    def receive_json(self, content):
        print(f"{self.channel_name} received data {content}")


class DoctorConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.accept()
        self.send_json({"type": "message", "message": "Hello doctor"})
        self.send_json({"type": "queue", "queue": [1, 2, 3, 4]})

    def disconnect(self, close_code):
        pass

    def receive_json(self, content):
        print(f"{self.channel_name} received data {content}")

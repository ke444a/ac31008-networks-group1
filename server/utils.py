class Channel:
    def __init__(self, name):
        self.name = name
        self.clients = set()

    def add_client(self, client):
        self.clients.add(client)

    def remove_client(self, client):
        self.clients.remove(client)


class User:
    def __init__(self, name):
        self.name = name
        self.channels = set()

    def join_channel(self, channel):
        self.channels.add(channel)

    def leave_channel(self, channel):
        self.channels.remove(channel)

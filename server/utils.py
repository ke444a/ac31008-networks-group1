from enum import Enum
from typing import Optional
class ResponseCode(Enum):
    RPL_WELCOME = "001"
    RPL_NAMREPLY = "353"
    RPL_ENDOFNAMES = "366"
    ERR_NOSUCHNICK = "401"
    ERR_NOSUCHCHANNEL = "403"
    ERR_CANNOTSENDTOCHAN = "404"
    ERR_UNKNOWNCOMMAND = "421"
    ERR_NONICKNAMEGIVEN = "431"
    ERR_ERRONEUSNICKNAME = "432"
    ERR_NICKNAMEINUSE = "433"

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

class Message:
    def __init__(self, sender: str, receiver: str, message: str, code: Optional[str] = None):
        self.sender = sender
        self.receiver = receiver
        self.message = message
        self.code = code

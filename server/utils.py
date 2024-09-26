from enum import Enum


class ResponseCode(Enum):
    RPL_WELCOME = "001"
    RPL_YOURHOST = "002"
    RPL_MYINFO = "004"
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
        # self.channels = set()

    # def join_channel(self, channel):
    #     self.channels.add(channel)

    # def leave_channel(self, channel):
    #     self.channels.remove(channel)
    
    def set_nickname(self, nickname):
        self.name = nickname

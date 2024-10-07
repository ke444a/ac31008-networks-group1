from enum import Enum
import asyncio

class NumericReplies(Enum):
    RPL_WELCOME = "001"
    RPL_YOURHOST = "002"
    RPL_MYINFO = "004"
    RPL_NOTOPIC = "331"
    RPL_TOPIC = "332"
    RPL_NAMREPLY = "353"
    RPL_ENDOFNAMES = "366"
    ERR_NOSUCHNICK = "401"
    ERR_NOTONCHANNEL = "442"
    ERR_NICKNAMEINUSE = "433"
    ERR_NONICKNAMEGIVEN = "431"
    ERR_NOPRIVILEGES = "481"
    
def log_message(client, message):
    print(f"\nSent to <{client.nickname}>: {message.strip()}")

class Client:
    def __init__(self, writer, nickname=None, username=None):
        self.writer = writer
        self.nickname = nickname
        self.username = username

    def send(self, message):
        log_message(self, message) 
        self.writer.write((message + "\r\n").encode())
        asyncio.create_task(self.writer.drain())

    def close(self):
        self.writer.close()
        asyncio.create_task(self.writer.wait_closed())

    def get_info(self):
        return f"{self.nickname} ({self.username})"

class Channel:
    def __init__(self, name):
        self.name = name
        self.members = set()
        self.topic = None

    def join(self, client):
        self.members.add(client)

    def part(self, client):
        self.members.discard(client)

    def broadcast(self, message, exclude=None):
        for client in self.members:
            if client != exclude:
                client.send(message)

    def is_empty(self):
        return len(self.members) == 0

def format_welcome_message(host, nick):
    return f":{host} {NumericReplies.RPL_WELCOME.value} {nick} :Welcome to the IRC server!\n"

def format_host_message(host, nick):
    return f":{host} {NumericReplies.RPL_YOURHOST.value} {nick} :Your host is {host}\n"

def format_myinfo_message(host, nick):
    return f":{host} {NumericReplies.RPL_MYINFO.value} {nick} {host}\n"

def format_names_message(host, nick, channel, names_list):
    return f":{host} {NumericReplies.RPL_NAMREPLY.value} {nick} = {channel} :{names_list}\n"

def format_no_such_nick_message(host, nick, target_nick):
    return f":{host} {NumericReplies.ERR_NOSUCHNICK.value} {nick} {target_nick} :No such nick/channel\n"

def format_not_on_channel_message(host, nick, channel):
    return f":{host} {NumericReplies.ERR_NOTONCHANNEL.value} {nick} {channel} :You're not on that channel\n"

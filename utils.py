from enum import Enum
import asyncio

class NumericReplies(Enum):
    RPL_WELCOME = "001"
    RPL_YOURHOST = "002"
    RPL_MYINFO = "004"
    RPL_CHANNELMODEIS = "324"
    RPL_NOTOPIC = "331"
    RPL_TOPIC = "332"
    RPL_NAMREPLY = "353"
    RPL_ENDOFNAMES = "366"
    ERR_NOSUCHNICK = "401"
    ERR_NOTONCHANNEL = "442"
    ERR_NICKNAMEINUSE = "433"
    ERR_NONICKNAMEGIVEN = "431"
    ERR_NEEDMOREPARAMS = "461"
    ERR_BANNEDFROMCHAN = "478"
    ERR_NOPRIVILEGES = "481"
    
def log_message(client, message):
    print(f"\nSent to <{client.nickname}>: {message.strip()}")

class Client:
    def __init__(self, writer, nickname=None, username=None):
        self.writer = writer
        self.nickname = nickname
        self.username = username
        self.banned_users = set()
        self.muted_users = set()

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
        self.banned_users = set()
        self.muted_users = set()

    def join(self, client):
        self.members.add(client)

    def part(self, client):
        self.members.discard(client)

    def broadcast(self, message, exclude=None):
        for client in self.members:
            if client != exclude:
                client.send(message)
    
    def ban_user(self, client):
        self.banned_users.add(client)

    def mute_user(self, client):
        self.muted_users.add(client)

    def unban_user(self, client):
        self.banned_users.discard(client)

    def unmute_user(self, client):
        self.muted_users.discard(client)

    def is_empty(self):
        return len(self.members) == 0
    
    def is_banned(self, client):
        return client in self.banned_users
    
    def is_muted(self, client):
        return client in self.muted_users


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

def format_need_more_params_message(host, nick, command):
    return f":{host} {NumericReplies.ERR_NEEDMOREPARAMS.value} {nick} {command} :Not enough parameters\n"

def format_banned_from_channel_message(host, nick, channel):
    return f":{host} {NumericReplies.ERR_BANNEDFROMCHAN.value} {nick} {channel} :Cannot join channel (banned)\n"

def format_no_privileges_message(host, nick):
    return f":{host} {NumericReplies.ERR_NOPRIVILEGES.value} {nick} :Permission Denied\n"

def format_mode_message(host, nick, channel, mode_symbol, target):
    return f":{host} {NumericReplies.RPL_CHANNELMODEIS.value} {nick} {channel} {mode_symbol} {target}\n"


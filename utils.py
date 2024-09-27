from enum import Enum

class NumericReplies(Enum):
    RPL_WELCOME = "001"
    RPL_YOURHOST = "002"
    RPL_MYINFO = "004"
    RPL_NAMREPLY = "353"
    RPL_ENDOFNAMES = "366"
    ERR_NOSUCHNICK = "401"
    ERR_NOTONCHANNEL = "442"
    ERR_NICKNAMEINUSE = "433"
    ERR_NONICKNAMEGIVEN = "431"

def format_welcome_message(host, nick):
    return f":{host} {NumericReplies.RPL_WELCOME.value} {nick} :Welcome to the IRC server!\n"

def format_host_message(host, nick):
    return f":{host} {NumericReplies.RPL_YOURHOST.value} {nick} :Your host is {host}\n"

def format_myinfo_message(host, nick):
    return f":{host} {NumericReplies.RPL_MYINFO.value} {nick} {host}\n"

def format_names_message(host, nick, channel, names_list):
    return f":{host} {NumericReplies.RPL_NAMREPLY.value} {nick} = {channel} :{names_list}\n"

def format_end_names_message(host, nick, channel):
    return f":{host} {NumericReplies.RPL_ENDOFNAMES.value} {nick} {channel} :End of /NAMES list.\n"

def format_no_such_nick_message(host, nick, target_nick):
    return f":{host} {NumericReplies.ERR_NOSUCHNICK.value} {nick} {target_nick} :No such nick/channel\n"

def format_not_on_channel_message(host, nick, channel):
    return f":{host} {NumericReplies.ERR_NOTONCHANNEL.value} {nick} {channel} :You're not on that channel\n"

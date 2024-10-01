import asyncio
import socket
from collections import defaultdict
import random

from utils import *
from utils import Channel, Client

class Server:
    def __init__(self, host='::1', port=6667):
        self.host = host
        self.port = port
        self.clients = {}
        self.channels = {}
        self.nicknames = set()

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        client = Client(writer)
        self.clients[addr] = client

        try:
            while True:
                data = await reader.readline()
                if not data:
                    break
                message = data.decode().strip()

                if message:
                    print(f"\nReceived from <{client.nickname}>: {message}")
                    self.process_message(message, client)

        except ConnectionResetError:
            print(f"Connection reset by {addr}. Disconnecting client.")
        except asyncio.CancelledError:
            pass
        finally:
            self.disconnect_client(client)
            
    def process_message(self, message, client):
        parts = message.split()
        command = parts[0].upper()

        if command == "NICK":
            self.set_nick(client, parts[1])
        elif command == "USER":
            self.set_user(client, parts[1:])
        elif command == "JOIN":
            channel_name = parts[1]
            self.join_channel(client, channel_name)
        elif command == "PART":
            channel_name = parts[1]
            self.part_channel(client, channel_name)
        elif command == "PRIVMSG":
            recipient = parts[1]
            msg = ' '.join(parts[2:])[1:]
            self.send_message(client, recipient, msg)
        elif command == "QUIT":
            self.disconnect_client(client)
        elif command == "TOPIC":
            if len(parts) >= 3:
                channel_name = parts[1]
                topic = ' '.join(parts[2:])[1:]
                self.set_topic(client, channel_name, topic)
            else:
                channel_name = parts[1]
                self.get_topic(client, channel_name)
        elif command == "NAMES":
            channel_name = parts[1]
            self.send_names_list(client, channel_name)

    def set_topic(self, client, channel_name, topic):
        if channel_name in self.channels:
            channel = self.channels[channel_name]
            channel.topic = topic
            topic_msg = f":{client.nickname} TOPIC {channel_name} :{topic}"
            channel.broadcast(topic_msg)
            client.send(f":{self.host} TOPIC {channel_name} :{topic}")
        else:
            client.send(format_not_on_channel_message(self.host, client.nickname, channel_name))

    def get_topic(self, client, channel_name):
        if channel_name in self.channels:
            topic = self.channels[channel_name].topic
            if topic:
                client.send(f":{self.host} {NumericReplies.RPL_TOPIC.value} {client.nickname} {channel_name} :{topic}")
            else:
                client.send(f":{self.host} {NumericReplies.RPL_NOTOPIC.value} {client.nickname} {channel_name} :No topic is set")
        else:
            client.send(format_not_on_channel_message(self.host, client.nickname, channel_name))

    def set_nick(self, client, nickname):
        original_nickname = nickname
        while nickname in self.nicknames:
            nickname = f"{original_nickname}{random.randint(1000, 9999)}"
        
        client.nickname = nickname
        self.nicknames.add(nickname)

        if nickname != original_nickname:
            notice_msg = f":{self.host} NOTICE * :Your nickname was changed to {nickname} because {original_nickname} is already in use\n"
            client.send(notice_msg)

    def set_user(self, client, user_details):
        if not client.nickname:
            error_msg = f":{self.host} {NumericReplies.ERR_NONICKNAMEGIVEN.value} * :No nickname given\n"
            client.send(error_msg)
            return

        client.username = ' '.join(user_details)
        client.send(format_welcome_message(self.host, client.nickname))
        client.send(format_host_message(self.host, client.nickname))
        client.send(format_myinfo_message(self.host, client.nickname))

    def join_channel(self, client, channel_name):
        if not channel_name.startswith("#"):
            error_msg = f":{self.host} {NumericReplies.ERR_NOSUCHNICK.value} {client.nickname} {channel_name} :No such channel\n"
            client.send(error_msg)
            return

        if channel_name not in self.channels:
            self.channels[channel_name] = Channel(channel_name)

        channel = self.channels[channel_name]
        channel.join(client)

        join_msg = f":{client.nickname} JOIN {channel_name}"
        channel.broadcast(join_msg)

        client.send(f":{client.nickname} JOIN {channel_name}")

        self.send_names_list(client, channel_name)

    def part_channel(self, client, channel_name):
        if channel_name in self.channels:
            channel = self.channels[channel_name]

            if client in channel.members:
                part_msg = f":{client.nickname} PART {channel_name}"
                channel.broadcast(part_msg, exclude=client)

                channel.part(client)
                client.send(part_msg)

                if channel.is_empty():
                    del self.channels[channel_name]
            else:
                client.send(format_not_on_channel_message(self.host, client.nickname, channel_name))
        else:
            client.send(format_not_on_channel_message(self.host, client.nickname, channel_name))

    def send_message(self, client, recipient, msg):
        if recipient.startswith("#"):
            if recipient in self.channels:
                channel = self.channels[recipient]
                if client in channel.members:
                    priv_msg = f":{client.nickname} PRIVMSG {recipient} :{msg}"
                    channel.broadcast(priv_msg, exclude=client)
                else:
                    client.send(format_not_on_channel_message(self.host, client.nickname, recipient))
            else:
                client.send(format_not_on_channel_message(self.host, client.nickname, recipient))
        else:
            target_client = None
            for addr, irc_client in self.clients.items():
                if irc_client.nickname == recipient:
                    target_client = irc_client
                    break

            if target_client:
                priv_msg = f":{client.nickname} PRIVMSG {recipient} :{msg}"
                target_client.send(priv_msg)
            else:
                client.send(format_no_such_nick_message(self.host, client.nickname, recipient))

    def disconnect_client(self, client):
        if client.nickname in self.nicknames:
            self.nicknames.remove(client.nickname)

        channels_to_update = list(self.channels.values())
        for channel in channels_to_update:
            if client in channel.members:
                part_msg = f":{client.nickname} PART {channel.name} :Disconnected"
                channel.broadcast(part_msg, exclude=client)
                channel.part(client)

                if channel.is_empty():
                    del self.channels[channel.name]

        if client.writer:
            try:
                client.writer.close()
                asyncio.create_task(self.safe_wait_closed(client.writer))

            except Exception as e:
                print(f"Error closing connection for {client.nickname}: {e}")

        addr_to_remove = None
        for addr, stored_client in self.clients.items():
            if stored_client == client:
                addr_to_remove = addr
                break

        if addr_to_remove:
            del self.clients[addr_to_remove]

    async def wait_closed(self, writer):
        try:
            await writer.wait_closed()
        except ConnectionResetError as e:
            print(f"Connection reset during close: {e}")
        except Exception as e:
            print(f"Unexpected error during close: {e}")

    def send_names_list(self, client, channel_name):
        if channel_name in self.channels:
            channel = self.channels[channel_name]
            names_list = " ".join([member.nickname for member in channel.members])
            client.send(f":{self.host} {NumericReplies.RPL_NAMREPLY.value} {client.nickname} = {channel_name} :{names_list}\n")
            client.send(f":{self.host} {NumericReplies.RPL_ENDOFNAMES.value} {client.nickname} {channel_name} :End of NAMES list\n") 
        else:
            client.send(format_not_on_channel_message(self.host, client.nickname, channel_name))

    async def start(self):
        server = await asyncio.start_server(self.handle_client, self.host, self.port, family=socket.AF_INET6)
        print(f'\nServing listening on {self.host}:{self.port} ...')
        async with server:
            await server.serve_forever()

if __name__ == "__main__":
    server = Server()
    asyncio.run(server.start())

import asyncio
import socket
import random
from datetime import datetime, timedelta

from utils import *
from utils import Channel, Client

# Class that handles the server logic
class Server:
    def __init__(self, host='::1', port=6667):
        self.host = host
        self.port = port
        self.clients = {}
        self.channels = {}
        self.nicknames = set()
        # Bot details
        self.bot_nickname = None
        # Secret key used to authenticate the bot
        self.bot_secret_key = "BOT_KEY"
        self.banned_users = {}
        self.muted_users = {}
        # Time interval to check for inactive clients
        self.check_interval = 10
        # List of commands that the server recognizes as client activity
        self.recognized_user_commands = ["NICK", "USER", "JOIN", "PART", "PRIVMSG", "QUIT", "TOPIC", "NAMES", "KICK", "MODE"]
    


    async def handle_client(self, reader, writer):
        # Retrieve the client's address to identify the client's source of connection
        addr = writer.get_extra_info('peername')
        client = Client(writer)
        client.last_active = datetime.now()
        self.clients[addr] = client

        try:
            while True:
                data = await reader.readline()
                if not data:
                    break
                message = data.decode().strip()

                if message:
                    # Update the client's last active time if they send a command
                    command = message.split()[0].upper()
                    if command in self.recognized_user_commands:
                        client.last_active = datetime.now()
                    print(f"\nReceived from <{client.nickname}>: {message}")
                    self.process_message(message, client)

        except ConnectionResetError:
            print(f"Connection reset by {addr}. Disconnecting client.")
        except asyncio.CancelledError:
            pass
        finally:
            await self.disconnect_client(client)

    async def check_inactive_clients(self):
        # Check for inactive clients every 10 seconds
        while True:
            await asyncio.sleep(self.check_interval)
            if not self.clients:
                continue
            now = datetime.now()
            clients_to_disconnect = []
            # Iterate over all clients and check if they are inactive for 1 minute
            for client in self.clients.values():
                # Skip the bot
                if client.nickname == self.bot_nickname:
                    continue
                if now - client.last_active > timedelta(seconds=60):
                    print(f"Client {client.nickname} inactive for 1 minute. Disconnecting.")
                    clients_to_disconnect.append(client)
            
            for client in clients_to_disconnect:
                await self.disconnect_client(client)
            
    def process_message(self, message, client):
        # Processing the commands from the client
        parts = message.split()
        command = parts[0].upper()

        if command == "NICK":
            new_nick = parts[1]
            self.set_nick(client, new_nick)
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
        elif command == "KICK":
            channel_name = parts[1]
            target_nickname = parts[2]
            self.kick_user(client, channel_name, target_nickname)
        elif command == "MODE":
            self.set_mode(client, parts[1:])
        elif command == "BOT_AUTH":
            print(f"DEBUG: Received BOT_AUTH command from {client.nickname}")
            self.authenticate_bot(client, parts[1:])
    
    def authenticate_bot(self, client, auth_parts):
        # Authenticate the bot using the secret key to distinguish it from regular clients
        if len(auth_parts) != 1:
            return
        
        secret = auth_parts[0]
        if secret == self.bot_secret_key:
            self.bot_nickname = client.nickname
            client.send(f":{self.host} 900 {client.nickname} :BOT_AUTH_SUCCESS {client.nickname}")
        else:
            client.send(f":{self.host} NOTICE {client.nickname} :Bot authentication failed")


    def set_topic(self, client, channel_name, topic):
        if channel_name in self.channels:
            channel = self.channels[channel_name]
            channel.topic = topic
            topic_msg = f":{client.nickname} TOPIC {channel_name} :{topic}"
            channel.broadcast(topic_msg)
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
        current_nickname = client.nickname

        if current_nickname == nickname:
            client.send(f":{self.host} {NumericReplies.ERR_NICKNAMEINUSE.value} {client.nickname} {nickname} NOTICE * :You already have that nick\n")
            return
        
        print(f"DEBUG: Current nicknames: {self.nicknames}")
        print(f"DEBUG: Client's current nickname: {client.nickname}")

        # Generate a new nickname if the desired one is already in use
        while nickname in self.nicknames and nickname != current_nickname:
            client.send(f":{self.host} {NumericReplies.ERR_NICKNAMEINUSE.value} {client.nickname} {nickname} nick is already in use generating a new one \n")
            nickname = f"{original_nickname}{random.randint(1000, 9999)}"

        if current_nickname in self.nicknames and current_nickname != nickname:
            print(f"DEBUG: Removing old nickname '{current_nickname}' from list.")
            self.nicknames.remove(current_nickname)

        self.nicknames.add(nickname)
        client.nickname = nickname
        print(f"DEBUG: Nickname changed to '{nickname}'")
        if nickname != original_nickname:
            notice_msg = f":{self.host} NOTICE * :Your nickname was changed to {nickname} because {original_nickname} is already in use\n"
            client.send(notice_msg)
        
        success_msg = f":{current_nickname} NICK :{nickname}\n"
        client.send(success_msg)
        print(f"DEBUG: Updated nicknames: {self.nicknames}")

    def set_user(self, client, user_details):
        if not client.nickname:
            error_msg = f":{self.host} {NumericReplies.ERR_NONICKNAMEGIVEN.value} * :No nickname given\n"
            client.send(error_msg)
            return

        # Sending welcome messages to the client
        client.username = ' '.join(user_details)
        client.send(format_welcome_message(self.host, client.nickname))
        client.send(format_host_message(self.host, client.nickname))
        client.send(format_myinfo_message(self.host, client.nickname))

    def join_channel(self, client, channel_name):
        if not channel_name.startswith("#"):
            error_msg = f":{self.host} {NumericReplies.ERR_NOSUCHNICK.value} {client.nickname} {channel_name} :No such channel\n"
            client.send(error_msg)
            return

        # Create a new channel if it doesn't exist
        if channel_name not in self.channels:
            self.channels[channel_name] = Channel(channel_name)

        channel = self.channels[channel_name]
        if channel.is_banned(client.nickname):
            client.send(format_banned_from_channel_message(self.host, client.nickname, channel_name))
            return

        channel.join(client)
        join_msg = f":{client.nickname} JOIN {channel_name}"
        channel.broadcast(join_msg)
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
                # Identify the channel and verify that the client is not muted or banned
                if channel.is_muted(client.nickname) or channel.is_banned(client.nickname):
                    client.send(f":{self.host} 404 {client.nickname} {recipient} :Cannot send to channel (You're muted)")
                elif client in channel.members:
                    if client.nickname in channel.banned_users:
                        client.send(f":{self.host} 404 {client.nickname} {recipient} :Cannot send to channel (You're banned)")
                    elif client.nickname in channel.muted_users:
                        client.send(f":{self.host} 404 {client.nickname} {recipient} :Cannot send to channel (You're muted)")
                    else:
                        priv_msg = f":{client.nickname} PRIVMSG {recipient} :{msg}"
                        channel.broadcast(priv_msg, exclude=client)
            else:
                client.send(format_not_on_channel_message(self.host, client.nickname, recipient))
        else:
            # Find the target cient by their nickname
            target_client = None
            for irc_client in self.clients.values():
                if irc_client.nickname == recipient:
                    target_client = irc_client
                    break
            
            # Send the message to the target client if found
            if target_client:
                priv_msg = f":{client.nickname} PRIVMSG {recipient} :{msg}"
                target_client.send(priv_msg)
            else:
                client.send(format_no_such_nick_message(self.host, client.nickname, recipient))

    
    def set_mode(self, client, parts):
        if len(parts) < 2:
            return

        channel_name = parts[0]
        mode = parts[1]
        target = parts[2] if len(parts) > 2 else None
        if channel_name not in self.channels:
            client.send(format_not_on_channel_message(self.host, client.nickname, channel_name))
            return

        # Process the mode change based on the mode flag
        channel = self.channels[channel_name]
        if mode == "+b" and target:
            self.ban_user(client, channel, target)
        elif mode == "-b" and target:
            self.unban_user(client, channel, target)
        elif mode == "+m" and target:
            self.mute_user(client, channel, target)
        elif mode == "-m" and target:
            self.unmute_user(client, channel, target)

    def kick_user(self, client, channel_name, target_nickname):
        print(f"Attempting to kick {target_nickname} from {channel_name} by {client.nickname}")
        if channel_name in self.channels:
            channel = self.channels[channel_name]
            # Identify the target client by their nickname
            target_client = None
            for member in channel.members:
                if member.nickname == target_nickname:
                    target_client = member
                    break

            if target_client:
                print(f"Found target client {target_client.nickname}")
                if client.nickname == target_client.nickname:
                    print(f"User is attempting to kick themseleves. Aborting the kick..")
                    client.send(f":{self.host} {NumericReplies.ERR_NOPRIVILEGES.value} {client.nickname} {channel_name} :You cannot kick yourself\n")
                    return

                kick_msg = f":{client.nickname} KICK {channel_name} {target_nickname} :Kicked by {client.nickname}"
                channel.broadcast(kick_msg)
                channel.part(target_client)
                target_client.send(kick_msg)
                if target_client.nickname == self.bot_nickname:
                    print(f"Bot kicked from {channel_name}. Rejoining....")
                    self.join_channel(target_client, channel_name)
            else:
                print(f"Target client {target_nickname} not found in {channel_name}")
                client.send(f":self.host {NumericReplies.ERR_NOSUCHNICK.value} {client.nickname} {target_nickname} :No such nick/channel\n")
        else:
            print(f"Channel {channel_name} not found")
            client.send(format_not_on_channel_message(self.host, client.nickname, channel_name))
    
    def ban_user(self, client, channel, target):
        if not channel.is_banned(target):
            channel.ban_user(target)
            channel.broadcast(format_mode_message(self.host, client.nickname, channel.name, "+b", target))

            target_client = None
            for member in channel.members:
                if member.nickname == target:
                    target_client = member
                    break
            
            # If the banned user is in the channel, remove them
            if target_client:
                self.part_channel(target_client, channel.name)


    def unban_user(self, client, channel, target):
        if channel.is_banned(target):
            channel.unban_user(target)
            channel.broadcast(format_mode_message(self.host, client.nickname, channel.name, "-b", target))

    def mute_user(self, client, channel, target):
        if not channel.is_muted(target):
            channel.mute_user(target)
            channel.broadcast(format_mode_message(self.host, client.nickname, channel.name, "+m", target))
    
    def unmute_user(self, client, channel, target):
        if channel.is_muted(target):
            channel.unmute_user(target)
            channel.broadcast(format_mode_message(self.host, client.nickname, channel.name, "-m", target))
    
    async def disconnect_client(self, client):
        if client.nickname in self.nicknames:
            self.nicknames.remove(client.nickname)

        for channel in self.channels.values():
            if client in channel.members:
                part_msg = f":{client.nickname} PART {channel.name} :Disconnected"
                channel.broadcast(part_msg, exclude=client)
                channel.part(client)
                if channel.is_empty():
                    # If the disconnected client was the last member of the channel, remove the channel
                    del self.channels[channel.name]

        # Close the client's connection
        if client.writer:
            try:
                client.writer.close()
                await client.writer.wait_closed()
            except Exception as e:
                print(f"Error closing connection for {client.nickname}: {e}")

        addr_to_remove = None
        for addr, stored_client in self.clients.items():
            if stored_client == client:
                addr_to_remove = addr
                break
        # Remove the client from the clients dictionary
        if addr_to_remove:
            del self.clients[addr_to_remove]

    async def wait_closed(self, writer):
        # Wait for the writer to close
        try:
            await writer.wait_closed()
        except ConnectionResetError as e:
            print(f"Connection reset during close: {e}")
        except Exception as e:
            print(f"Unexpected error during close: {e}")

    def send_names_list(self, client, channel_name):
        # Retrieve the channel and send the list of names to the client
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
        # Task to check for inactive clients
        asyncio.create_task(self.check_inactive_clients())
        async with server:
            await server.serve_forever()

if __name__ == "__main__":
    server = Server()
    asyncio.run(server.start())

import socket
from typing import Dict, Optional
from utils import Channel, User, ResponseCode
import threading

HOST = 'localhost'
PORT = 6667


class Server:
    def __init__(self, host: str = HOST, port: int = PORT):
        self.host = host
        self.port = port
        self.server_socket = self.create_server_socket()
        self.clients: Dict[socket.socket, User] = {}
        self.channels: Dict[str, Channel] = {}

    # Starts the server socket with IPv6
    def create_server_socket(self) -> socket.socket:
        server_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.port))
        server_socket.listen()
        return server_socket

    # Accepts a connection from a client
    def accept_connection(self) -> None:
        client_socket, client_address = self.server_socket.accept()
        print(f"Connection from {client_address} has been established.")
        return (client_socket, client_address)
    
    # Handles a client connection
    def handle_client(self, client_socket: socket.socket) -> None:
        while True:
            try:
                # Parses the data from the client
                data = client_socket.recv(1024).decode("utf-8").strip()
                if not data:
                    break
                
                command, *args = data.split()
                self.handle_command(command, args, client_socket, self.clients.get(client_socket, None))
            except Exception as e:
                print(f"Error handling client: {e}")
                break
        
        self.cleanup_client(client_socket, self.clients.get(client_socket, None))

    def cleanup_client(self, client_socket: socket.socket, user: Optional[User]) -> None:
        for channel in self.channels.values():
            if user in channel.clients:
                channel.remove_client(user)

        if user:
            del self.clients[client_socket]
        client_socket.close()
    
    def handle_command(self, command: str, args: list, client_socket: socket.socket, user: Optional[User]) -> None:
        command_handlers = {
            "NICK": self.handle_nickname,
            "JOIN": self.handle_join_channel,
            "PART": self.handle_leave_channel,
            "PRIVMSG": self.handle_send_private_message
        }
        
        # Gets appropriate handler for the provided command
        handler = command_handlers.get(command)
        if handler:
            handler(args, client_socket, user)
        else:
            self.send_message_to_client(client_socket=client_socket, message=f":server {ResponseCode.ERR_UNKNOWNCOMMAND.value} {user.name} {command} :Unknown command")

    def handle_nickname(self, args: list, client_socket: socket.socket, user: Optional[User]) -> None:
        if not args:
            self.send_message_to_client(client_socket=client_socket, message=f":server {ResponseCode.ERR_NONICKNAMEGIVEN.value} {user.name} :NICK command requires a nickname.")
            return
        
        nickname = args[0]
        if nickname in self.clients:
            self.send_message_to_client(client_socket=client_socket, message=f":server {ResponseCode.ERR_NICKNAMEINUSE.value} {user.name} {nickname} :Nickname is already in use.")
            return
        
        # If the user just connected, create a new user object with the nickname
        if user:
            user.set_nickname(nickname)
        else:
            new_user = User(nickname)
            self.clients[client_socket] = new_user
        self.send_message_to_client(client_socket=client_socket, message=f":server {ResponseCode.RPL_WELCOME.value} {nickname} :Your nickname is set to {nickname}")

    def handle_join_channel(self, args: list, client_socket: socket.socket, user: Optional[User]) -> None:
        if not args or not user:
            return
        
        # Send a message to the client about joining a channel
        channel_name = args[0]
        channel = self.channels.setdefault(channel_name, Channel(channel_name))
        channel.add_client(user)
        self.send_message_to_client(client_socket, f":{user.name}!{user.name}@{self.host} JOIN {channel_name}")
        self.send_message_to_client(client_socket, f":server {ResponseCode.RPL_WELCOME.value} {user.name} :You joined {channel_name}")
        self.handle_users_in_channel(channel, client_socket, user)
    
    # Sends a list of users in a channel to the client
    def handle_users_in_channel(self, channel: Channel, client_socket: socket.socket, user: Optional[User]) -> None:
        user_list = " ".join([client.name for client in channel.clients])
        self.send_message_to_client(client_socket, f":server {ResponseCode.RPL_NAMREPLY.value} {user.name} {channel.name} :{user_list}")
        self.send_message_to_client(client_socket, f":server {ResponseCode.RPL_ENDOFNAMES.value} {user.name} {channel.name} :End of /NAMES list.")


    # Handles a client leaving a channel
    def handle_leave_channel(self, args: list, client_socket: socket.socket, user: Optional[User]) -> None:
        if not args or not user:
            return
        
        channel_name = args[0]
        if channel_name in self.channels and user in self.channels[channel_name].clients:
            self.channels[channel_name].remove_client(user)
            self.send_message_to_client(client_socket, f":{user.name}!{user.name}@{self.host} PART {channel_name}")
            self.send_message_to_client(client_socket, f":server {ResponseCode.RPL_WELCOME.value} {user.name} :You have left {channel_name}")

    # Handles a client sending a private message to another client
    def handle_send_private_message(self, args: list, client_socket: socket.socket, user: Optional[User]) -> None:
        if len(args) < 2 or not user:
            self.send_message_to_client(client_socket, f":server {ResponseCode.ERR_NONICKNAMEGIVEN.value} {user.name} :PRIVMSG requires a target and message.")
            return
        
        # If target starts with #, it is a channel message
        # Otherwise, it is a private message
        target, message = args[0], " ".join(args[1:])
        if target.startswith("#"):
            self.send_channel_message(target, user, message)
        else:
            self.send_private_message(target, user, message)

    # Sends a message to all clients in a channel
    def send_channel_message(self, channel_name: str, sender: User, message: str) -> None:
        if channel_name in self.channels:
            channel = self.channels[channel_name]
            self.broadcast_message(channel, sender, message)
        else:
            self.send_message_to_client(self.get_client_socket(sender), f":server {ResponseCode.ERR_NOSUCHCHANNEL.value} {sender.name} {channel_name} :Error. Channel {channel_name} does not exist.")

    # Sends a private message to a specific client
    def send_private_message(self, recipient_name: str, sender: User, message: str) -> None:
        # Retrieves the socket for the recipient
        recipient_socket = self.get_user_socket(recipient_name)
        if recipient_socket:
            self.send_message_to_client(recipient_socket, f":{sender.name}!{sender.name}@{self.host} PRIVMSG {recipient_name} :{message}")
        else:
            self.send_message_to_client(self.get_client_socket(sender), f":server {ResponseCode.ERR_NOSUCHNICK.value} {sender.name} {recipient_name} :Error. User {recipient_name} does not exist.")

    def get_user_socket(self, username: str) -> Optional[socket.socket]:
        for soc, user in self.clients.items():
            if user.name == username:
                return soc
        return None

    def get_client_socket(self, user: User) -> Optional[socket.socket]:
        for soc, client_user in self.clients.items():
            if client_user == user:
                return soc
        return None
    
    def broadcast_message(self, channel: Channel, sender: User, message: str) -> None:
        for client in channel.clients:
            if client != sender:
                client_socket = self.get_client_socket(client)
                if client_socket:
                    self.send_message_to_client(client_socket, f":{sender.name}!{sender.name}@{self.host} PRIVMSG {client.name} :{message}")
                
    def send_message_to_client(self, client_socket: socket.socket, message: str) -> None:
        try:
            print(f">>> Sending message: {message}")
            client_socket.send(message.encode("utf-8"))
        except Exception as e:
            print(f"### Failed to send message to {client_socket}: {e}")

    # Starts the server
    def start(self) -> None:
        print(f"Server started on {self.host}:{self.port}")
        while True:
            try:
                client_socket, client_address = self.server_socket.accept()
                print(f"Connection from {client_address} has been established.")
                # Sends a welcome message to the client
                self.send_message_to_client(client_socket=client_socket,
                                            message=f":server {ResponseCode.RPL_WELCOME.value} * :Welcome to the IRC server")
                self.send_message_to_client(client_socket=client_socket,
                                            message=f":server {ResponseCode.RPL_YOURHOST.value} * :Your host is {self.host}")
                self.send_message_to_client(client_socket=client_socket,
                                            message=f":server {ResponseCode.RPL_MYINFO.value} * :{self.host} {self.port} {self.host} {self.port}")
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))
                client_thread.start()
            except KeyboardInterrupt:
                print(">>> Server shutting down...")
                break
            except Exception as e:
                print(f"### Error in main server loop: {e}")
        
        self.close()
    
    # Closes the server
    def close(self) -> None:
        for client_socket in self.clients.keys():
            client_socket.close()
        self.server_socket.close()
        print(">>> Server closed.")

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

    def create_server_socket(self) -> socket.socket:
        server_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.port))
        server_socket.listen()
        return server_socket

    def accept_connection(self) -> None:
        client_socket, client_address = self.server_socket.accept()
        print(f"Connection from {client_address} has been established.")

        self.send_message_to_client(client_socket, "server", "*", "Welcome to the IRC server", ResponseCode.RPL_WELCOME.value)
        self.handle_client(client_socket)
    
    def handle_client(self, client_socket: socket.socket) -> None:
        while True:
            try:
                data = client_socket.recv(1024).decode("utf-8").strip()
                if not data:
                    break
                
                command, *args = data.split()
                self.handle_command(command, args, client_socket, self.clients.get(client_socket, None))
            except Exception as e:
                print(f"Error handling client: {e}")
                break
        
        self._cleanup_client(client_socket, self.clients.get(client_socket, None))

    def _cleanup_client(self, client_socket: socket.socket, user: Optional[User]) -> None:
        if user:
            for channel in user.channels:
                channel.remove_client(user)
            del self.clients[client_socket]
        client_socket.close()
    
    def handle_command(self, command: str, args: list, client_socket: socket.socket, user: Optional[User]) -> None:
        command_handlers = {
            "NICK": self._handle_nickname,
            "JOIN": self._handle_join_channel,
            "PART": self._handle_leave_channel,
            "PRIVMSG": self._handle_send_private_message
        }
        
        handler = command_handlers.get(command)
        if handler:
            handler(args, client_socket, user)
        else:
            receiver = '*' if not user else user.name
            self.send_message_to_client(client_socket, "server", receiver, f"Unknown command: {command}", ResponseCode.ERR_UNKNOWNCOMMAND.value)

    def _handle_nickname(self, args: list, client_socket: socket.socket, user: Optional[User]) -> None:
        if not args:
            self.send_message_to_client(client_socket, "server", user.name, "NICK command requires a nickname.", ResponseCode.ERR_NONICKNAMEGIVEN.value)
            return
        nickname = args[0]
        if nickname in self.clients:
            self.send_message_to_client(client_socket, "server", user.name, f"Nickname {nickname} is already in use.", ResponseCode.ERR_NICKNAMEINUSE.value)
            return
        user = User(nickname)
        self.clients[client_socket] = user
        self.send_message_to_client(client_socket, "server", user.name, f"Your nickname is set to {nickname}", ResponseCode.RPL_WELCOME.value)

    def _handle_join_channel(self, args: list, client_socket: socket.socket, user: Optional[User]) -> None:
        if not args or not user:
            return
        
        channel_name = args[0]
        channel = self.channels.setdefault(channel_name, Channel(channel_name))
        channel.add_client(user)
        user.join_channel(channel)
        self.send_message_to_client(client_socket, "server", user.name, f"Welcome to the channel {channel_name}", ResponseCode.RPL_WELCOME.value)
        self.send_message_to_client(client_socket, f":{user.name}!{user.name}@{self.host} JOIN {channel_name}")
    
        self.send_message_to_client(client_socket, "server", user.name, f"Welcome to the channel {channel_name}", ResponseCode.RPL_WELCOME.value)
    
        self.send_message_to_client(client_socket, f"{user.name}!{user.name}@{self.host}", channel_name, "")

        user_list = " ".join([client.name for client in channel.clients])
        self.send_message_to_client(client_socket, "server", user.name, f"= {channel_name} :{user_list}", ResponseCode.RPL_NAMREPLY.value)
        
        # End of names list
        self.send_message_to_client(client_socket, "server", user.name, f"{channel_name} :End of /NAMES list.", ResponseCode.RPL_ENDOFNAMES.value)


    def _handle_leave_channel(self, args: list, client_socket: socket.socket, user: Optional[User]) -> None:
        if not args or not user:
            return
        channel_name = args[0]
        if channel_name in self.channels and user in self.channels[channel_name].clients:
            self.channels[channel_name].remove_client(user)
            user.leave_channel(self.channels[channel_name])
            self.send_message_to_client(client_socket, "server", user.name, f"You have left {channel_name}", ResponseCode.RPL_WELCOME.value)

    def _handle_send_private_message(self, args: list, client_socket: socket.socket, user: Optional[User]) -> None:
        if len(args) < 2 or not user:
            self.send_message_to_client(client_socket, "server", user.name, "PRIVMSG requires a target and message.", ResponseCode.ERR_NONICKNAMEGIVEN.value)
            return
        
        target, message = args[0], " ".join(args[1:])
        if target.startswith("#"):
            self._send_channel_message(target, user, message)
        else:
            self._send_private_message(target, user, message)

    def _send_channel_message(self, channel_name: str, sender: User, message: str) -> None:
        if channel_name in self.channels:
            channel = self.channels[channel_name]
            self.broadcast_message(channel, sender, message)
        else:
            self.send_message_to_client(self._get_client_socket(sender), "server", sender.name, f"Error. Channel {channel_name} does not exist.", ResponseCode.ERR_NOSUCHCHANNEL.value)

    def _send_private_message(self, recipient_name: str, sender: User, message: str) -> None:
        recipient_socket = self._get_user_socket(recipient_name)
        if recipient_socket:
            self.send_message_to_client(recipient_socket, sender.name, recipient_name, message)
        else:
            self.send_message_to_client(self._get_client_socket(sender), "server", sender.name, f"Error. User {recipient_name} does not exist.", ResponseCode.ERR_NOSUCHNICK.value)

    def _get_user_socket(self, username: str) -> Optional[socket.socket]:
        for socket, user in self.clients.items():
            if user.name == username:
                return socket
        return None

    def _get_client_socket(self, user: User) -> Optional[socket.socket]:
        for socket, client_user in self.clients.items():
            if client_user == user:
                return socket
        return None
    
    def broadcast_message(self, channel: Channel, sender: User, message: str) -> None:
        for client in channel.clients:
            if client != sender:
                client_socket = self._get_client_socket(client)
                if client_socket:
                    self.send_message_to_client(client_socket, sender.name, client.name, message)
                
    def send_message_to_client(self, client_socket: socket.socket, sender: str, receiver: str, message: str, code: Optional[str] = None) -> None:
        try:
            message_str = f":{sender}{' ' + code if code else ''} {receiver} :{message}\r\n"
            print(f">>> Sending message: {message_str}")
            client_socket.send(message_str.encode("utf-8"))
        except Exception as e:
            print(f"### Failed to send message to {client_socket}: {e}")

    def start(self) -> None:
        print(f"Server started on {self.host}:{self.port}")
        while True:
            try:
                client_socket, client_address = self.server_socket.accept()
                print(f"Connection from {client_address} has been established.")
                
                self.send_message_to_client(client_socket, "server", "*", "Welcome to the IRC server", ResponseCode.RPL_WELCOME.value)
                
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))
                client_thread.start()
            except KeyboardInterrupt:
                print(">>> Server shutting down...")
                break
            except Exception as e:
                print(f"### Error in main server loop: {e}")
        
        self.close()
    
    def close(self) -> None:
        for client_socket in self.clients.keys():
            client_socket.close()
        self.server_socket.close()
        print(">>> Server closed.")
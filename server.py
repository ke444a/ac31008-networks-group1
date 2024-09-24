import socket
import threading

# server info
HOST = "::"
PORT = "6667"
clients = {}
channels = {}

def manage_client(client_socket, client_address):
    print(f"Client connected: {client_address}")
    
    # get client's info when they connect to the server
    username = client_socket.recv(1024).decode('utf-8')
    clients[client_socket] = {"address": client_address, "username": username, "channel": None}
    
    # was gonna make it automatically join #general chat but we need to use command line arguments for this anyway
    # manage_client_join("general", client_socket, username)

    while True:
        try:
            message = client_socket.recv(1024).decode('utf-8')
            if message:
                manage_message(message, client_socket, username)
            else:
                break
        except Exception as e:
            print(f"Error: {e}")
            break

    # deals with when a client disconnects
    client_socket.close()
    current_channel = clients[client_socket].get("channel")
    if current_channel:
        channels[current_channel].remove(client_socket)  # removes client from channel when they disconnect
    del clients[client_socket]  # removes client from client list when they disconnect
    broadcast_message(f"{username} left the chat.", client_socket, current_channel)
    print(f"Client disconnected: {client_address}")

# deals with all types of input to the server
def manage_message(message, sender_socket, username):
    if message.startswith("/join "):
        # if input is the join command then it calls the function that joins clients to a channel
        channel_name = message.split()[1]
        manage_client_join(channel_name, sender_socket, username)
    elif message.startswith("/part"):
        # If input is the part command, call the function to leave the channel
        manage_client_part(sender_socket, username)
    elif message.startswith("/msg "):
        # if input is the msg then it's a private message
        # extracts the username and sends the message to the intended recipient
        parts = message.split(' ', 2)
        if len(parts) == 3:
            recipient_username = parts[1]
            private_msg = parts[2]
            manage_private_message(recipient_username, private_msg, sender_socket, username)
    elif message == "/list":
        # calls functions that lists all channels
        list_channels(sender_socket)
    else:
        # if the input isn't a command, then it's a message
        # then it sends the message to all clients in the same channel
        current_channel = clients[sender_socket].get("channel")
        if current_channel:
            broadcast_message(f"{username}: {message}", sender_socket, current_channel)
        else:
            sender_socket.send("Use /join [channel] to join a channel.".encode('utf-8'))

# adds/joins client to a channel
def manage_client_join(channel_name, client_socket, username):
    current_channel = clients[client_socket].get("channel")
    if current_channel:
        # removes client from current channel first before adding them to a new channel
        channels[current_channel].remove(client_socket)

    # adds client to the new channel
    if channel_name not in channels:
        channels[channel_name] = []
    channels[channel_name].append(client_socket)
    clients[client_socket]["channel"] = channel_name

    # broadcast_messages new client's join message to all other clients in the same new channel
    broadcast_message(f"{username} joined the channel {channel_name}", client_socket, channel_name)
    client_socket.send(f"Joined channel #{channel_name}".encode('utf-8'))

# disconnects client from a channel
def manage_client_part(client_socket, username):
    current_channel = clients[client_socket].get("channel")
    if current_channel:
        channels[current_channel].remove(client_socket)  # removes the client from the current channel
        clients[client_socket]["channel"] = None 
        broadcast_message(f"{username} left the channel {current_channel}.", client_socket, current_channel)
        client_socket.send(f"You left the channel {current_channel}.".encode('utf-8'))
    else:
        client_socket.send("You are already not in a channel.".encode('utf-8'))

# sends private message to chosen recipient
def manage_private_message(recipient_username, message, sender_socket, sender_username):
    recipient_socket = None
    for client_socket, info in clients.items():
        if info["username"] == recipient_username:
            recipient_socket = client_socket
            break

    if recipient_socket:
        recipient_socket.send(f"Private message from {sender_username}: {message}".encode('utf-8'))
    else:
        sender_socket.send(f"User {recipient_username} not found.".encode('utf-8'))

# lists all channels in the server
def list_channels(client_socket):
    if channels:
        channel_list = "List of channels:\n" + "\n".join([f"#{channel}" for channel in channels.keys()])
        client_socket.send(channel_list.encode('utf-8'))
    else:
        client_socket.send("Nono channels available.".encode('utf-8'))

# sends message to client sin the same channel
def broadcast_message(message, sender_socket, channel_name):
    for client in channels.get(channel_name, []):
        if client != sender_socket:
            client.send(message.encode('utf-8'))

def run_server():
    server_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    server_socket.bind(("::", 6667)) 
    server_socket.listen(5)
    print(f"Server listening on [{HOST}]:{PORT} ...") 

    while True:
        client_socket, client_address = server_socket.accept()

        # again i read that threading was recommended so i implemented it here too
        # creates new thread for handling each client which allows more than one client to message
        # at the same time
        client_thread = threading.Thread(target=manage_client, args=(client_socket, client_address))
        client_thread.start()

if __name__ == "__main__":
    run_server()

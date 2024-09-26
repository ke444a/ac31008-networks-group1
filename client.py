import socket
import threading

# get client's username
username = input("Enter your username: ")

# deals with a client receving a message from the server
def receive_messages(client_socket):
    while True:
        try:
            message = client_socket.recv(1024).decode('utf-8')
            if message:
                print(message)
            else:
                break
        except Exception as e:
            print(f"Error receiving message: {e}")
            break

# deals with sending a message to the server or in case of privately messaging another client
def send_messages(client_socket):
    while True:
        message = input()
        if message.startswith('/msg '): # private message command
            recipient, *msg = message[5:].split()
            private_message = f"PRIVATE {recipient} {' '.join(msg)}"
            client_socket.send(private_message.encode('utf-8'))
        elif message.startswith('/join '): # join channel command
            client_socket.send(message.encode('utf-8'))
        elif message == "/list": # channel list command
            client_socket.send(message.encode('utf-8'))
        else:
            client_socket.send(message.encode('utf-8'))

def main():
    client_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    # i made it use local ipv6 just for easier testing but we can change this later
    # port is 6667 as instructed
    client_socket.connect(("::1", 6667)) 

    # sends username to the server
    client_socket.send(username.encode('utf-8'))

    # seen some youtube video that recommended threading when dealing with receving and sending messages
    # so i implemented it
    # basically threading for receving messages
    receive_thread = threading.Thread(target=receive_messages, args=(client_socket,))
    receive_thread.start()

    # and threading for sending messages 
    send_thread = threading.Thread(target=send_messages, args=(client_socket,))
    send_thread.start()

if __name__ == "__main__":
    main()

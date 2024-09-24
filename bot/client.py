import socket

HOST = 'localhost'
PORT = 6667

class Client:
    def __init__(self, host=HOST, port=PORT):
        self.client_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        self.client_socket.connect((host, port))

    def send_message(self, message):
        self.client_socket.sendall(message.encode('utf-8'))

    def receive_message(self):
        return self.client_socket.recv(1024).decode('utf-8')

    def close(self):
        self.client_socket.close()


import socket

HOST = 'localhost'
PORT = 6667

class Server:
    def __init__(self, host=HOST, port=PORT):
        self.server_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        self.server_socket.bind((host, port))
        self.server_socket.listen()

    def accept_connection(self):
        self.client_socket, self.client_address = self.server_socket.accept()
        print(f"Connection from {self.client_address} has been established.")

    def close(self):
        self.server_socket.close()


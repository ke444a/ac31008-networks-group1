import socket
import random 
import threading
import time

CHANNEL = "#test"
BOT_NAME = "SuperBot"
FUN_FACTS = [ 
   "A cloud weighs around a million tonnes",
   "The first oranges were not orange",
   "The shortest war in history lasted 38 minutes",
   "The Eiffel Tower can be 15 cm taller during the summer",
   "The largest snowflake ever recorded reportedly measured 15 inches across"
]

HOST = "::1"
PORT = 6667

class Client:
    def __init__(self):
        try:
            self.client_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            self.client_socket.connect((HOST, PORT))
            print("Connected to the server with socket")
        except Exception as e:
            print(f"Error connecting to the server: {e}")

    def send_message(self, message):
        self.client_socket.sendall(message.encode('utf-8'))

    def receive_message(self):
        return self.client_socket.recv(1024).decode('utf-8')
    
    def handle_commands(self, message):
        sender, content = message.split(":", 1)
        sender = sender.split("!")[0]

        if content.startswith("!hello"):
            response = f"Hello {sender}!"
            self.send_message(f"PRIVMSG {CHANNEL} :{response}\r\n")
        # elif content.startswith("!slap"):
            # determine users in the channel somehow
            # users = []
            # rewrite this
            # users_in_channel = [user for user in users_in_channel if user != BOT_NAME and user != sender]

            # if len(content.split()) > 1:
            #     target_user = content.split()[1]
            #     if target_user in users_in_channel:
            #         response = f"{sender} slaps {target_user} around a bit with a large trout"
            #         self.send_message(f"PRIVMSG {CHANNEL} :{response}\r\n")
            #     else:
            #         response = f"{sender} slaps {target_user} around a bit with a large trout"
            #         self.send_message(f"PRIVMSG {CHANNEL} :{response}\r\n")
            # else:
            #     target_user = random.choice(users_in_channel)
            #     response = f"{sender} slaps {target_user} around a bit with a large trout"
            #     self.send_message(f"PRIVMSG {CHANNEL} :{response}\r\n")
    
    def respond_to_private_message(self, sender):
        random_fact = random.choice(FUN_FACTS)
        self.send_message(f"PRIVMSG {sender} :{random_fact}\r\n")

    def receive_private_message(self):
        while True:
            try:
                message = self.receive_message()
                print(f"Bot received: {message}")  # Debug print
                if message.startswith("PING"):
                    pong_reply = f"PONG {message.split()[1]}\r\n"
                    self.send_message(pong_reply)
                    print(f"Bot sent: {pong_reply}")  # Debug print
                elif "PRIVMSG" in message:
                    parts = message.split()
                    sender = parts[0].split('!')[0][1:]
                    target = parts[2]
                    content = ' '.join(parts[3:])[1:]
                    
                    if target == CHANNEL:
                        if content.startswith("!"):
                            self.handle_commands(f"{sender}:{content}")
                    else:
                        self.respond_to_private_message(sender)

            except Exception as e:
                print(f"Error receiving message: {e}")
                break

    def join_channel_and_announce(self):    
        try:
            self.send_message(f"NICK {BOT_NAME}\r\n")
            time.sleep(0.1)

            self.send_message(f"JOIN {CHANNEL}\r\n")
            time.sleep(0.1)

            self.send_message(f"PRIVMSG {CHANNEL} :Hello! I am {BOT_NAME} Type !hello or !slap to see what happens\r\n")
        except Exception as e:
            print(f"Error in join and announce function: {e}")

    def start_bot(self):
        self.join_channel_and_announce()
        receive_thread = threading.Thread(target=self.receive_private_message)
        receive_thread.start()

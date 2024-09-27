import socket
import argparse
import random

class IRCBot:
    def __init__(self, host, port, name, channel):
        self.host = host
        self.port = port
        self.name = name
        self.channel = channel
        self.sock = None

        # jokes are from:
        # https://www.countryliving.com/life/entertainment/a36178514/hilariously-funny-jokes/
        self.jokes = [
            "Did you hear about the new squirrel diet? It's just nuts.!",
            "I made song about tortilla once, now it's more like a wrap.",
            "Did you hear about the spatula's hot new flame? It met the grill of its dreams.",
            "Did you know corduroy pillows are in style? They're making headlines.",
            "What do call a criminal landing an airplane? Condescending."
        ]

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        print(f'Connecting to {self.host}:{self.port} as {self.name}...')
        
        self.send_message(f"NICK {self.name}")
        self.send_message(f"USER {self.name} 0 * :{self.name}")
        
        self.join_channel(self.channel)

        self.listen_for_messages()

    def send_message(self, message):
        self.sock.sendall((message + "\r\n").encode())
        print(f'Sent: {message}')

    def join_channel(self, channel):
        self.send_message(f"JOIN {channel}")
        print(f'Joined channel: {channel}')

    def listen_for_messages(self):
        while True:
            response = self.sock.recv(2048).decode('utf-8', errors='replace')
            if response:
                print(f"Received: {response.strip()}")
                self.handle_server_response(response.strip())

    def handle_server_response(self, response):
        
        if response.startswith(':'):
            parts = response.split()
            if len(parts) > 3 and parts[1] == 'PRIVMSG':
                sender = parts[0].split('!')[0][1:]  
                message = ' '.join(parts[3:])[1:]  
                
                if message.startswith('!'):
                    command = message[1:]  
                    self.handle_command(sender, command)
            
            if len(parts) > 3 and parts[1] == 'PRIVMSG' and parts[2] == self.name:
                private_message = ' '.join(parts[3:])[1:]  
                self.respond_to_private_message(sender, private_message)

    def handle_command(self, sender, command):
        if command == 'hello':
            self.send_message(f"PRIVMSG {self.channel} :Hello, {sender}!")
        elif command.startswith('slap'):
            target = command.split()[1] if len(command.split()) > 1 else None
            self.slap_user(sender, target)

    def slap_user(self, sender, target):
        
        if target and target != self.name:
            slap_msg = f"{sender} slaps {target} with a trout!"
        else:
            slap_msg = f"{sender} slaps themselves with a trout!"

        self.send_message(f"PRIVMSG {self.channel} :{slap_msg}")

    def respond_to_private_message(self, sender, message):
        
        random_joke = random.choice(self.jokes)
        self.send_message(f"PRIVMSG {sender} :{random_joke}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', type=str, required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--name', type=str, required=True)
    parser.add_argument('--channel', type=str, required=True)

    args = parser.parse_args()

    bot = IRCBot(args.host, args.port, args.name, args.channel)
    bot.connect()
    
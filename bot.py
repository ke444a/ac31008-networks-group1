import socket
import argparse
import random

class Bot:
    def __init__(self, host, port, name, channel):
        self.host = host
        self.port = port
        self.name = name
        self.channel = channel
        self.sock = None
        self.topic = None
        self.channel_members = []  # Initialize channel_members here

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
        self.sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)  # Enable IPv6
        self.sock.connect((self.host, self.port))
        print(f'\nConnecting to {self.host}:{self.port} as {self.name}...')

        self.send_message(f"NICK {self.name}")
        self.send_message(f"USER {self.name} 0 * :{self.name}")

        self.join_channel(self.channel)

        self.listen_for_messages()

    def send_message(self, message):
        self.sock.sendall((message + "\r\n").encode())
        print(f'\nSent: {message}')

    def join_channel(self, channel):
        self.send_message(f"JOIN {channel}")

    def listen_for_messages(self):
        while True:
            response = self.sock.recv(2048).decode('utf-8', errors='replace')
            if response:
                # Split the response into individual lines
                lines = response.strip()
                for line in lines.splitlines():
                    if line:
                        print(f"\nReceived: {line.strip()}")  # Print each line received
                        self.handle_server_response(line.strip())

    def handle_server_response(self, response):
        parts = response.split()
        
        # print("")
        # print(parts)
        # Handle the NAMES response from the server
        if len(parts) > 3 and parts[1] == '353':  # RPL_NAMREPLY
            # Clear previous members
            self.channel_members = []

            # Extract names starting from the fifth part, while ensuring they are valid nicknames
            names = parts[4:]  
            # Filter out any invalid names
            for name in names:
                # Strip any leading ':' character
                if name.startswith(':'):
                    name = name[1:]  # Remove leading ':'
                if name and not name.startswith('#'):  # Ensure it's not a channel name
                    self.channel_members.append(name)
                    
            print(f"\nUsers in {self.channel}: {self.channel_members}")

        elif len(parts) > 3 and parts[1] == '366':  # RPL_ENDNAMES
            # print(f"End of NAMES list for {self.channel}")
            pass

        # Handle topic response from the server
        elif len(parts) > 3 and parts[1] == '332':
            topic = ' '.join(parts[3:])[1:]
            self.send_message(f"PRIVMSG {self.channel} :Current topic for {self.channel}: {topic}")
        
        elif len(parts) > 3 and parts[1] == '331':
            self.send_message(f"PRIVMSG {self.channel} :No topic is set for {self.channel}")

        elif len(parts) > 3 and parts[1] == 'PRIVMSG':
            sender = parts[0].split('!')[0][1:]
            message = ' '.join(parts[3:])[1:]

            if message.startswith('!'):
                command = message[1:]
                self.handle_command(sender, command)

            if len(parts) > 3 and parts[1] == 'PRIVMSG' and parts[2] == self.name:
                private_message = ' '.join(parts[3:])[1:]
                self.respond_to_private_message(sender, private_message)
        
        if len(parts) > 3 and parts[1] == 'TOPIC':
            if parts[3] == ':No':
                self.topic = "No topic is set."
            else:
                self.topic = ' '.join(parts[3:])[1:]

    def handle_command(self, sender, command):
        if command.startswith('hello'):
            self.send_message(f"PRIVMSG {self.channel} :Hello, {sender}!")
        elif command.startswith('slap'):
            target = command.split()[1] if len(command.split()) > 1 else None
            self.slap_user(sender, target)
        elif command.startswith('topic'):
            self.handle_topic_command(sender, command)

    def handle_topic_command(self, sender, command):
        parts = command.split(' ', 1)

        if len(parts) == 1:
            # Request the topic from the server
            self.send_message(f"TOPIC {self.channel}")
        else:
            new_topic = parts[1]
            self.send_message(f"TOPIC {self.channel} :{new_topic}")
            print(f"Set new topic for {self.channel}: {new_topic}")

    def slap_user(self, sender, target):
        # Request the names before slapping to ensure we have the latest list
        self.send_message(f"NAMES {self.channel}")  # Request names to update the list

        # Now we need to handle the slap after the names are received
        users_in_channel = self.get_users_in_channel(sender)

        if target and target in users_in_channel:
            slap_msg = f"{sender} slaps {target} with a trout!"
        elif target:
            # slap_msg = f"{sender} tried to slap {target}, but they're not in the channel!"
            slap_msg = f"{sender} slaps themselves with a trout!"
        else:
            # If no target specified, slap a random user
            if users_in_channel:
                target = random.choice([user for user in users_in_channel if user != sender and user != self.name])
                slap_msg = f"{sender} slaps {target} with a trout!"
            else:
                slap_msg = f"{sender} has no one to slap!"

        self.send_message(f"PRIVMSG {self.channel} :{slap_msg}")

    def get_users_in_channel(self, sender):
        # Return a list of users excluding the sender and the bot
        return [user for user in self.channel_members if user != sender and user != self.name]

    def get_channel_members(self):
        # This should ideally call the server or be managed in your bot state
        # For this example, let's assume you send a command to the server to get the current channel members
        self.send_message(f"NAMES {self.channel}")  # Assuming there's a NAMES command to request channel members

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

    bot = Bot(args.host, args.port, args.name, args.channel)
    bot.connect()

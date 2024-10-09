import socket
import argparse
import random
import time
import threading
from utils import NumericReplies

class Bot:
    def __init__(self, host, port, name, channel):
        self.host = host
        self.port = port
        self.name = name
        self.channel = channel
        self.sock = None
        self.topic = None
        self.channel_members = [] 
        self.active_poll = None
        self.poll_votes = {}
        self.poll_voters = set()  # New set to keep track of voters
        self.is_muted = False

    def connect(self):
        self.sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM) 
        self.sock.connect((self.host, self.port))
        print(f'\nConnecting to {self.host}:{self.port} as {self.name}...')

        self.send_message(f"NICK {self.name}")
        self.send_message(f"USER {self.name} 0 * :{self.name}")

        self.join_channel(self.channel)

        self.listen_for_messages()

    def send_message(self, message):
        if self.is_muted:
            self.sock.sendall((f"PRIVMSG {self.channel} :Bot is muted, unmute the bot to talk!\r\n").encode())
            print(f"Attempted to send message while muted: {message}")
            return
        self.sock.sendall((message + "\r\n").encode())
        print(f'\nSent: {message}')

    def join_channel(self, channel):
        self.send_message(f"JOIN {channel}")

    def listen_for_messages(self):
        try:
            while True:
                response = self.sock.recv(2048).decode('utf-8', errors='replace')
                if response:
                    lines = response.strip()
                    for line in lines.splitlines():
                        if line:
                            print(f"\nReceived: {line.strip()}") 
                            self.handle_server_response(line.strip())

        except ConnectionResetError as e:
            print(f"Connection lost: {e}")
            self.disconnect()
        except Exception as e:
            print(f"Unexpected error: {e}")
            self.disconnect()

    def disconnect(self):
        print("Disconnected from the server.")
        try:
            self.sock.close()
        except Exception as e:
            print(f"Error while closing: {e}")

    def handle_server_response(self, response):
        parts = response.split()
        
        if len(parts) > 3 and parts[1] == NumericReplies.RPL_NAMREPLY.value: 
            self.channel_members = []
            names = parts[4:]  
            for name in names:
                if name.startswith(':'):
                    name = name[1:]
                if name and not name.startswith('#'): 
                    self.channel_members.append(name)
                    
            print(f"\nUsers in {self.channel}: {self.channel_members}")

        elif len(parts) > 3 and parts[1] == NumericReplies.RPL_ENDOFNAMES.value: 
            pass

        elif len(parts) > 3 and parts[1] == NumericReplies.RPL_TOPIC.value:
            topic = ' '.join(parts[4:])[1:]
            self.send_message(f"PRIVMSG {self.channel} :Current topic for {self.channel}: {topic}")
            print({topic})
        
        elif len(parts) > 3 and parts[1] == NumericReplies.RPL_NOTOPIC.value:
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
        
        elif len(parts) > 3 and parts[1] == 'MODE':
            channel = parts[2]
            mode = parts[3]
            target = parts[4] if len(parts) > 4 else None
            self.handle_mode_change(channel, mode, target)

        if len(parts) <= 3 and parts[1] == 'JOIN':
            self.send_message(f"NAMES {self.channel}")
        
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
        elif command.startswith('poll'):
            self.handle_poll_command(sender, command)
        elif command.startswith('vote'):
            self.handle_vote_command(sender, command)
        elif command.startswith('kick'):
            self.handle_kick_command(sender, command)
        elif command.startswith('ban'):
            self.handle_ban_command(sender, command)
        elif command.startswith('unban'):
            self.handle_unban_command(sender, command)
        elif command.startswith('mute'):
            self.handle_mute_command(sender, command)
        elif command.startswith('unmute'):
            self.handle_unmute_command(sender, command)

    def handle_kick_command(self, sender, command):
        parts = command.split(' ', 1)
        if len(parts) < 2:
            self.send_message(f"PRIVMSG {self.channel} :Invalid kick format. Usage: !kick <nickname>")
            return

        target = parts[1].strip()
        print(f"Attempting to kick {target} from {self.channel} by {sender}")
        self.send_message(f"KICK {self.channel} {target} :Kicked by {sender}")
        
    def handle_ban_command(self, sender, command):
        parts = command.split()
        if len(parts) < 2:
            self.send_message(f"PRIVMSG {self.channel} :Usage: !ban <nickname>")
            return
        target = parts[1]
        self.send_message(f"MODE {self.channel} +b {target}")
        self.send_message(f"PRIVMSG {self.channel} :{target} has been banned from {self.channel}")
    
    def handle_mute_command(self, sender, command):
        parts = command.split()
        if len(parts) < 2:
            self.send_message(f"PRIVMSG {self.channel} :Usage: !mute <nickname>")
            return
        target = parts[1]
        self.send_message(f"MODE {self.channel} +m {target}")
        self.send_message(f"PRIVMSG {self.channel} :{target} has been muted in {self.channel}")
        if target == self.name:
            self.is_muted = True

    def handle_unban_command(self, sender, command):
        parts = command.split()
        if len(parts) < 2:
            self.send_message(f"PRIVMSG {self.channel} :Usage: !unban <nickname>")
            return
        target = parts[1]
        self.send_message(f"MODE {self.channel} -b {target}")
        self.send_message(f"PRIVMSG {self.channel} :{target} has been unbanned from {self.channel}")

    def handle_unmute_command(self, sender, command):
        parts = command.split()
        if len(parts) < 2:
            self.send_message(f"PRIVMSG {self.channel} :Usage: !unmute <nickname>")
            return
        target = parts[1]
        self.send_message(f"MODE {self.channel} -m {target}")
        self.send_message(f"PRIVMSG {self.channel} :{target} has been unmuted in {self.channel}")
        if target == self.name:
            self.is_muted = False

    def handle_poll_command(self, sender, command):
        parts = command.split(' ', 1)
        if len(parts) < 2 or ';' not in parts[1]:
            self.send_message(f"PRIVMSG {self.channel} :Invalid poll format. Usage: !poll \"<question>\" <option1>;<option2>;<option3>...;")
            return
        try:
            first_quote_index = parts[1].index('"')
            second_quote_index = parts[1].index('"', first_quote_index + 1)
            question = parts[1][first_quote_index + 1:second_quote_index].strip()
            options_part = parts[1][second_quote_index + 1:].strip()
            options = [opt.strip() for opt in options_part.split(';') if opt.strip()]

            if len(options) < 2:
                self.send_message(f"PRIVMSG {self.channel} :Error: A poll must have at least 2 options.")
                return

            if self.active_poll:
                self.send_message(f"PRIVMSG {self.channel} :There is already an active poll. Wait for it to end.")
                return

            self.active_poll = {
                'question': question,
                'options': options,
                'start_time': time.time(),
                'duration': 45
            }
            self.poll_votes = {}
            self.poll_voters = set()  # Reset voters for new poll

            poll_message = f"Poll started by {sender}\nQuestion:\"{question}\"\nOptions: {', '.join(options)}\nType !vote <option> to vote.\nTime limit: 45 seconds."
            for msg in poll_message.split('\n'):
                self.send_message(f"PRIVMSG {self.channel} :{msg}")
        
            # Start a timer to end the poll
            threading.Timer(45, self.handle_end_poll, args=[self.name]).start()

        except ValueError:
            self.send_message(f"PRIVMSG {self.channel} :Invalid poll format. Usage: !poll \"<question>\" <option1>;<option2>;<option3>...;")
            return

    def handle_end_poll(self, sender):
        if not self.active_poll:
            self.send_message(f"PRIVMSG {self.channel} :No active poll to end.")
            return

        total_votes = sum(self.poll_votes.values())
        results = []
        for option in self.active_poll['options']:
            votes = self.poll_votes.get(option, 0)
            percentage = (votes / total_votes) * 100 if total_votes > 0 else 0
            results.append(f"{option}: {votes} votes ({percentage:.2f}%)")

        results_message = f"Poll ended for '{self.active_poll['question']}'\nResults:\n{', '.join(results)}"
        for msg in results_message.split('\n'):
            self.send_message(f"PRIVMSG {self.channel} :{msg}")
        self.active_poll = None
        self.poll_votes = {}
        self.poll_voters = set()
    
    def handle_vote_command(self, sender, command):
        if not self.active_poll:
            self.send_message(f"PRIVMSG {self.channel} :No active poll.")
            return

        if sender in self.poll_voters:
            self.send_message(f"PRIVMSG {self.channel} :{sender}, you have already voted in this poll.")
            return

        parts = command.split(' ', 1)
        if len(parts) < 2:
            self.send_message(f"PRIVMSG {self.channel} :Invalid vote format. Usage: !vote <option>")
            return

        vote = parts[1].strip().lower()
        for option in self.active_poll['options']:
            if vote == option.lower():
                self.poll_votes[option] = self.poll_votes.get(option, 0) + 1
                self.poll_voters.add(sender)
                self.send_message(f"PRIVMSG {self.channel} :{sender}, your vote has been registered for {option}.")
                return

        self.send_message(f"PRIVMSG {self.channel} :{sender}, invalid vote option. Valid options: {', '.join(self.active_poll['options'])}")


    def handle_mode_change(self, channel, mode, target):
        if mode == '+b' and target:
            print(f"{target} has been banned from {channel}")
        elif mode == '-b' and target:
            print(f"{target} has been unbanned from {channel}")
        elif mode == '+m' and target:
            print(f"{target} has been muted in {channel}")
        elif mode == '-m' and target:
            print(f"{target} has been unmuted in {channel}")

    def handle_topic_command(self, sender, command):
        parts = command.split(' ', 1)

        if len(parts) == 1:
            self.send_message(f"TOPIC {self.channel}")
        else:
            new_topic = parts[1]
            self.send_message(f"TOPIC {self.channel} :{new_topic}")
            print(f"Set new topic for {self.channel}: {new_topic}")

    def slap_user(self, sender, target):
        self.send_message(f"NAMES {self.channel}")

        users_in_channel = self.get_users_in_channel(sender)

        if target == self.name:
            slap_msg = f"Ugh, {sender}... You're so bad at this game..."
        elif target and target in users_in_channel:
            slap_msg = f"{sender} slaps {target} with a trout!"
        elif target:
            slap_msg = f"{sender} slaps themselves with a trout!"
        else:
            if users_in_channel:
                target = random.choice([user for user in users_in_channel if user != sender and user != self.name])
                slap_msg = f"{sender} slaps {target} with a trout!"
            else:
                slap_msg = f"{sender} has no one to slap!"

        self.send_message(f"PRIVMSG {self.channel} :{slap_msg}")

    def get_users_in_channel(self, sender):
        return [user for user in self.channel_members if user != sender and user != self.name]

    def get_channel_members(self):
        self.send_message(f"NAMES {self.channel}") 

    # jokes are from:
    # https://www.countryliving.com/life/entertainment/a36178514/hilariously-funny-jokes/
    def respond_to_private_message(self, sender, message):
        random_joke = self.get_joke_from_file()
        self.send_message(f"PRIVMSG {sender} :{random_joke}")

    def get_joke_from_file(self):
        try:
            with open('jokes.txt', 'r') as file:
                jokes = file.readlines()
                jokes = [joke.strip() for joke in jokes if joke.strip()]
                if jokes:
                    return random.choice(jokes)
                else:
                    return "Jokes text file is empty."
        except FileNotFoundError:
            return "Jokes text file not found."

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', type=str, required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--name', type=str, required=True)
    parser.add_argument('--channel', type=str, required=True)

    args = parser.parse_args()

    bot = Bot(args.host, args.port, args.name, args.channel)
    bot.connect()
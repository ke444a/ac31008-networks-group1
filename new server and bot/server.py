import asyncio
from collections import defaultdict
from utils import *

class IRCServer:
    def __init__(self, host='localhost', port=6667):
        self.host = host
        self.port = port
        self.clients = {}
        self.channels = defaultdict(set)

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        self.clients[addr] = (writer, None, None)

        try:
            while True:
                data = await reader.readline()
                message = data.decode().strip()

                if message:
                    self.log(f"Received: {message} from {self.get_nick(addr)}")
                    self.process_message(message, addr)

        except asyncio.CancelledError:
            pass
        finally:
            self.clients.pop(addr, None)
            for channel in self.channels.values():
                channel.discard(addr)
            writer.close()
            await writer.wait_closed()

    def process_message(self, message, addr):
        parts = message.split()
        command = parts[0].upper()

        if command == "NICK":
            self.set_nick(addr, parts[1])
        elif command == "USER":
            self.set_user(addr, parts[1:])
        elif command == "JOIN":
            channel = parts[1]
            self.join_channel(addr, channel)
        elif command == "PART":
            channel = parts[1]
            self.part_channel(addr, channel)
        elif command == "PRIVMSG":
            recipient = parts[1]
            msg = ' '.join(parts[2:])[1:]  # Skip the colon
            self.send_message(addr, recipient, msg)
        elif command == "QUIT":
            self.handle_quit(addr)

    def get_nick(self, addr):
        writer, nick, _ = self.clients.get(addr, (None, None, None))
        return nick if nick else str(addr)

    def set_nick(self, addr, nick):
        writer, _, user = self.clients[addr]
        self.clients[addr] = (writer, nick, user)

    def set_user(self, addr, user_details):
        writer, nick, _ = self.clients[addr]
        if not nick:
            error_msg = f":{self.host} {NumericReplies.ERR_NONICKNAMEGIVEN.value} * :No nickname given\n"
            writer.write(error_msg.encode())
            self.log(f"Sent: {error_msg.strip()}")
            asyncio.create_task(writer.drain())
            return
        
        self.clients[addr] = (writer, nick, ' '.join(user_details))

        # Send welcome messages
        writer.write(format_welcome_message(self.host, nick).encode())
        self.log(f"Sent: {format_welcome_message(self.host, nick).strip()}")
        asyncio.create_task(writer.drain())
        
        writer.write(format_host_message(self.host, nick).encode())
        self.log(f"Sent: {format_host_message(self.host, nick).strip()}")
        
        writer.write(format_myinfo_message(self.host, nick).encode())
        self.log(f"Sent: {format_myinfo_message(self.host, nick).strip()}")

    def handle_quit(self, addr):
        writer, nick, _ = self.clients.get(addr, (None, None, None))
        if nick:
            quit_msg = f":{nick} QUIT :Client Quit\n"
            for client_writer, _, _ in self.clients.values():
                client_writer.write(quit_msg.encode())
                self.log(f"Sent: {quit_msg.strip()}")

        self.log(f"{self.get_nick(addr)} quit the server.")
        self.clients.pop(addr, None)

    def join_channel(self, addr, channel):
        writer, nick, _ = self.clients[addr]
        if not channel.startswith("#"):
            error_msg = f":{self.host} {NumericReplies.ERR_NOTONCHANNEL.value} {nick} {channel} :No such channel\n"
            writer.write(error_msg.encode())
            self.log(f"Sent: {error_msg.strip()}")
            asyncio.create_task(writer.drain())
            return

        if channel not in self.channels:
            self.channels[channel] = set()
        
        if addr in self.channels[channel]:
            # Already in channel, do nothing
            return

        self.channels[channel].add(addr)

        join_msg = f":{nick} JOIN {channel}\n"
        for member in self.channels[channel]:
            member_writer, _, _ = self.clients[member]
            member_writer.write(join_msg.encode())
            self.log(f"Sent: {join_msg.strip()}")
            asyncio.create_task(member_writer.drain())

        self.send_names_list(addr, channel)

    def part_channel(self, addr, channel):
        writer, nick, _ = self.clients[addr]
        if channel in self.channels and addr in self.channels[channel]:
            self.channels[channel].discard(addr)
            part_msg = f":{nick} PART {channel}\n"
            for member in self.channels[channel]:
                member_writer, _, _ = self.clients[member]
                member_writer.write(part_msg.encode())
                self.log(f"Sent: {part_msg.strip()}")
                asyncio.create_task(member_writer.drain())

            writer.write(f":{nick} PART {channel}\n".encode())
            self.log(f"Sent: :{nick} PART {channel}")
            asyncio.create_task(writer.drain())

            if not self.channels[channel]:
                del self.channels[channel]
        else:
            error_msg = format_not_on_channel_message(self.host, nick, channel)
            writer.write(error_msg.encode())
            self.log(f"Sent: {error_msg.strip()}")
            asyncio.create_task(writer.drain())

    def send_message(self, addr, recipient, msg):
        writer, nick, _ = self.clients[addr]

        # Check if the recipient is a nickname or a channel
        if recipient.startswith("#"):
            if recipient in self.channels and addr in self.channels[recipient]:
                message = f":{nick} PRIVMSG {recipient} :{msg}\n"
                for member in self.channels[recipient]:
                    if member != addr:
                        member_writer, _, _ = self.clients[member]
                        member_writer.write(message.encode())
                        self.log(f"Sent: {message.strip()}")
                        asyncio.create_task(member_writer.drain())
            else:
                error_msg = format_not_on_channel_message(self.host, nick, recipient)
                writer.write(error_msg.encode())
                self.log(f"Sent: {error_msg.strip()}")
                asyncio.create_task(writer.drain())
                return  # Prevent further processing if channel is not valid
        else:
            target_addr = None
            for client_addr, (client_writer, client_nick, _) in self.clients.items():
                if client_nick == recipient:
                    target_addr = client_addr
                    break
            
            if target_addr and target_addr in self.clients:
                message = f":{nick} PRIVMSG {recipient} :{msg}\n"
                target_writer, _, _ = self.clients[target_addr]
                target_writer.write(message.encode())
                self.log(f"Sent: {message.strip()}")
                asyncio.create_task(target_writer.drain())
            else:
                error_msg = format_no_such_nick_message(self.host, nick, recipient)
                writer.write(error_msg.encode())
                self.log(f"Sent: {error_msg.strip()}")
                asyncio.create_task(writer.drain())
                return  # Prevent further processing if nickname does not exist

    def send_names_list(self, addr, channel):
        writer, nick, _ = self.clients[addr]
        names_list = " ".join([self.clients[member][1] for member in self.channels[channel]])

        names_msg = format_names_message(self.host, nick, channel, names_list)
        end_msg = format_end_names_message(self.host, nick, channel)
        
        writer.write(names_msg.encode())
        writer.write(end_msg.encode())
        self.log(f"Sent: {names_msg.strip()}")
        self.log(f"Sent: {end_msg.strip()}")
        asyncio.create_task(writer.drain())

    async def start(self):
        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        print(f'Serving on {self.host}:{self.port}')
        async with server:
            await server.serve_forever()

    def log(self, message):
        print(message)

if __name__ == "__main__":
    irc_server = IRCServer()
    asyncio.run(irc_server.start())

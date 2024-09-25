import asyncio
from collections import defaultdict

class IRCServer:
    def __init__(self, host='127.0.0.1', port=6667):
        self.host = host
        self.port = port
        self.clients = {}
        self.channels = defaultdict(set)

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info('peername')
        self.clients[addr] = writer
        print(f'Client connected from {addr}')

        # Send welcome message
        writer.write(f":localhost 001 {addr[0]} :Welcome to the IRC server!\n".encode())
        await writer.drain()

        try:
            while True:
                data = await reader.readline()
                message = data.decode().strip()

                if message:
                    print(f"Received: {message} from {addr}")
                    self.process_message(message, addr)

        except asyncio.CancelledError:
            pass
        finally:
            print(f'Client disconnected from {addr}')
            self.clients.pop(addr, None)
            for channel in self.channels.values():
                channel.discard(addr)
            writer.close()
            await writer.wait_closed()

    def process_message(self, message, addr):
        parts = message.split()
        command = parts[0].upper()

        if command == "JOIN":
            channel = parts[1]
            self.join_channel(addr, channel)
        elif command == "PART":
            channel = parts[1]
            self.part_channel(addr, channel)
        elif command == "PRIVMSG":
            recipient = parts[1]
            msg = ' '.join(parts[2:])[1:]  # Skip the colon
            self.send_message(addr, recipient, msg)

    def join_channel(self, addr, channel):
        if not channel.startswith("#"):
            error_msg = f":localhost 403 {addr[0]} {channel} :No such channel\n"  # Error message for invalid channel
            self.clients[addr].write(error_msg.encode())
            asyncio.create_task(self.clients[addr].drain())
            print(f"{addr} tried to join invalid channel {channel}.")
            return

        if channel not in self.channels:
            self.channels[channel] = set()
        self.channels[channel].add(addr)

        # Notify the channel about the new member
        join_msg = f":{addr[0]} JOIN {channel}\n"
        for member in self.channels[channel]:
            self.clients[member].write(join_msg.encode())
            asyncio.create_task(self.clients[member].drain())

        print(f"{addr} joined {channel}")

    def part_channel(self, addr, channel):
        if channel in self.channels and addr in self.channels[channel]:
            self.channels[channel].discard(addr)
            part_msg = f":{addr[0]} PART {channel}\n"
            for member in self.channels[channel]:
                self.clients[member].write(part_msg.encode())
                asyncio.create_task(self.clients[member].drain())

            # Notify the user that they have parted
            self.clients[addr].write(f":{addr[0]} PART {channel}\n".encode())
            asyncio.create_task(self.clients[addr].drain())

            print(f"{addr} left {channel}")

            # Remove the channel if it's empty
            if not self.channels[channel]:
                del self.channels[channel]  # Clean up the channel if it's empty
                print(f"Channel {channel} is now empty and removed.")
        else:
            print(f"{addr} tried to PART {channel}, but was not in it.")

    def send_message(self, addr, recipient, msg):
        # Check if the recipient is a channel or a user
        if recipient.startswith("#"):  # Channel
            if recipient in self.channels and addr in self.channels[recipient]:
                message = f":{addr[0]} PRIVMSG {recipient} :{msg}\n"
                for member in self.channels[recipient]:
                    if member != addr:  # Don't send the message back to the sender
                        self.clients[member].write(message.encode())
                        asyncio.create_task(self.clients[member].drain())
        else:  # Private message to a user
            target_addr = None
            for client_addr in self.clients:
                if client_addr[0] == recipient:  # Match based on the username (IP part only)
                    target_addr = client_addr
                    break
            if target_addr and target_addr in self.clients:
                message = f":{addr[0]} PRIVMSG {recipient} :{msg}\n"
                self.clients[target_addr].write(message.encode())
                asyncio.create_task(self.clients[target_addr].drain())

    async def start(self):
        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        print(f'Serving on {self.host}:{self.port}')
        async with server:
            await server.serve_forever()

if __name__ == "__main__":
    irc_server = IRCServer()
    asyncio.run(irc_server.start())

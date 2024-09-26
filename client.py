import socket
import random 
import threading
import time

CHANNEL = "#test" # default channel for now
BOT_NAME = "SuperBot" # bot name for now
FUN_FACTS = [ "A cloud weighs around a million tonnes"
              "The first oranges were not orange",
              "The shortest war in history lasted 38 minutes",
              "The Eiffel Tower can be 15 cm taller during the summer",
              "The largest snowflake ever recorded reportedly measured 15 inches across",]

# to handle certain commands 

def handle_commands(message, client_socket):

   # to parse out the sender and message
   sender, content = message.split(":", 1)

   # to remove any extra characters from the sender
   sender = sender.split("!")[0]

   if content.startswith("!hello"):
     response = f"Hello {sender}!"
     client_socket.send(f"PRIVMSG {CHANNEL} :{response}\r\n".encode('utf-8'))

   elif content.startswith("!slap"):
     users_in_channel = ['user1', 'user2', 'user3']
     users_in_channel = [user for user in users_in_channel if user != BOT_NAME and user != sender]

     if len(content.split()) > 1:
       target_user = content.split()[1]
       if target_user in users_in_channel:
         response = f"{sender} slaps {target_user} around a bit with a large trout"
         client_socket.send(f"PRIVMSG {CHANNEL} :{response}\r\n".encode('utf-8'))
       else:
         response = f"{sender} slaps {target_user} around a bit with a large trout"
         client_socket.send(f"PRIVMSG {CHANNEL} :{response}\r\n".encode('utf-8'))

     else:
        target_user = random.choice(users_in_channel)
        response = f"{sender} slaps {target_user} around a bit with a large trout"

        client_socket.send(f"PRIVMSG {CHANNEL} :{response}\r\n".encode('utf-8'))
   
# to respond to a private message with a fun fact

def respond_to_private_message(sender, client_socket):
    random_fact = random.choice(FUN_FACTS)
    private_message = f"PRIVMSG {sender} :{random_fact}\r\n"
    client_socket.send(private_message.encode('utf-8'))


# to receive the private message from server 

def receive_private_message(client_socket):
   while True:
    try:
         message = client_socket.recv(1024).decode('utf-8')
         print(f"Received: {message}")  # Debug print
         if message.startswith("PING"):
            pong_reply = f"PONG {message.split()[1]}\r\n"
            client_socket.send(pong_reply.encode('utf-8'))
            print(f"Sent: {pong_reply}")  # Debug print

         elif "PRIVMSG" in message:
           parts = message.split()
           sender = parts[0].split('!')[0][1:]
           target = parts[2]
           content = ' '.join(parts[3:])[1:]  # Remove leading ':'
           
           if target == CHANNEL:
              if content.startswith("!"):
                 handle_commands(f"{sender}:{content}", client_socket)
           else:
              respond_to_private_message(sender, client_socket)

    except Exception as e:
            print(f"Error receiving message: {e}")
            break

            
# to send inital join command and additional bot features 
def join_channel_and_announce(client_socket):    
 try:
    nick_command = f"NICK {BOT_NAME}\r\n"  
    client_socket.send(nick_command.encode('utf-8'))
    print(f"Command sent: {nick_command}")
    time.sleep(5)

    user_command = f"USER {BOT_NAME} 0 * :{BOT_NAME}\r\n"
    client_socket.send(user_command.encode('utf-8'))
    print(f"Command sent: {user_command}")
    time.sleep(5)

    join_command = f"JOIN {CHANNEL}\r\n"
    client_socket.send(join_command.encode('utf-8'))
    print(f"Command sent: {join_command}")
    time.sleep(5)

    privmsg_command = f"PRIVMSG {CHANNEL} :Hello! I am {BOT_NAME} type !hello or !slap to see what happens\r\n"
    client_socket.send(privmsg_command.encode('utf-8'))
    print(f"Command sent: {privmsg_command}")
 except Exception as e:
    print(f"Error in join and announce function: {e}")
       

def send_messages(client_socket):
    while True:
        message = input()
        if message.startswith('/msg '): # private message command
            recipient, *msg = message[5:].split()
            private_message = f"PRIVATE {recipient} {' '.join(msg)}"
            client_socket.send(private_message.encode('utf-8'))
        elif message.startswith('/join '): # join channel command
            client_socket.send(f"JOIN {message.split()[1]}\r\n".encode('utf-8'))
        elif message == "/list": # channel list command
            client_socket.send(f"LIST\r\n".encode('utf-8'))
        else:
            client_socket.send(f"PRIVMSG {CHANNEL} :{message}\r\n".encode('utf-8'))


def main():
    client_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    print("Attempting to connect to the server...")
    try:
        client_socket.connect(("::1", 6667))
        print("Connected to the server. Joining the channel...")
    except Exception as e:
        print(f"Error connecting to the server: {e}")
        return

    join_channel_and_announce(client_socket)


    receive_thread = threading.Thread(target=receive_private_message, args=(client_socket,))
    send_thread = threading.Thread(target=send_messages, args=(client_socket,))

    receive_thread.start()
    send_thread.start()

    receive_thread.join()
    send_thread.join()

if __name__ == "__main__":
    main()

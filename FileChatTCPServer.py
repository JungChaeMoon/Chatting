#
# FileChatTCPServer.py
# 20151631 Jung Chaemoon
#

from socket import *
import time
import threading
import re
import base64

serverStart = time.time()
serverPort = 21631
serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

# version specification
server_version = 1
client_version = 1
client_id_socket_dict = dict()
client_socket_sem_dict = dict()
# Header Definitions for Roles and Commands
SUCCESS = 's'
FAIL = 'f'
JOIN = 'j'
MESSAGE = 'm'
USERS = 'u'
WHISPER = 'w'
EXIT = 'e'
VERSION = 'v'
RENAME = 'r'
RTT = 't'
F_FILE = 'd'
W_FILE = 'c'
FIRST = '1'
LAST = '0'
ING = '2'
TEST = '3'
remain = ''
nickname_flag = True


# Because tcp works in the stream, it created a layer to use message protocol.
def send(clientSocket, message):

    escape = '<semicolon>'
    message = message.replace(';', escape)
    message = message + ';'

    client_socket_sem_dict[clientSocket].acquire()
    clientSocket.send(message.encode())
    client_socket_sem_dict[clientSocket].release()


def recv(clientSocket):
    global end, remain
    escape = '<semicolon>'

    while True:
        if ';' in remain:
            remain_split = remain.split(';', maxsplit=1)

            if len(remain_split) > 1:
                remain = remain_split[1]
                return remain_split[0].replace(escape, ';')
            elif len(remain_split) == 1:
                remain += remain_split[0]
        else:
            message = clientSocket.recv(2048)

            if not message:
                return ''
            end = time.time()
            message = message.decode()
            remain += message



def thread(connectionSocket, clientAddress, clientNumber):

    global  nickname_flag

    try:
        # Send a welcome message to the client and then broadcast the message that the client is connected.
        client_id_socket_dict[clientNumber] = [connectionSocket, clientAddress]
        client_socket_sem_dict[connectionSocket] = threading.Semaphore(1)
        serverMessage = SUCCESS + '\n' + "welcome {} to cau-net class chat room at {}, {}. You are {}th user".format(clientNumber, serverSocket.getsockname()[0], serverSocket.getsockname()[1], len(client_id_socket_dict))
        # connectionSocket.send(serverMessage.encode())
        send(connectionSocket, serverMessage)
        serverMessage = MESSAGE + '\n' + '{} joined. There are {} users in the chat room'.format(clientNumber, len(client_id_socket_dict))
        for nickname, client in client_id_socket_dict.items():
            if nickname == clientNumber:
                continue
            # client[0].send(serverMessage.encode())
            send(client[0], serverMessage)
        print("{} joined. There are {} users connected".format(clientNumber, str(len(client_id_socket_dict))))

        while True:
            # Receive packets.
            # message = connectionSocket.recv(2048)
            message = recv(connectionSocket)
            # message = message.decode(errors='ignore')
            # If the packet is empty, consider the client to be down and disconnect and wait for the connection again.
            if not message:
                del client_id_socket_dict[clientNumber]
                connectionSocket.close()
                serverMessage = MESSAGE + '\n' + "{} is disconnected. There are {} users in the chat room.".format(clientNumber, len(client_id_socket_dict))
                for nickname, client in client_id_socket_dict.items():
                    if nickname == clientNumber:
                        continue
                    # client[0].send(serverMessage.encode())
                    send(client[0], serverMessage)
                print("{} left. There are {} users now".format(clientNumber, len(client_id_socket_dict)))
                break
            # If the message contains the phrase "i hate processor", it is kicked out.
            header, body = message.split('\n', maxsplit=1)
            # print(body)
            if 'i hate professor' in body.lower():
                serverMessage = MESSAGE + '\n' + clientNumber + '> ' + body
                for nickname, client in client_id_socket_dict.items():
                    if nickname == clientNumber:
                        continue
                    # client[0].send(serverMessage.encode())
                    send(client[0], serverMessage)
                del client_id_socket_dict[clientNumber]
                connectionSocket.close()
                serverMessage = MESSAGE + '\n' + "{} is disconnected. There are {} users in the chat room.".format(clientNumber, len(client_id_socket_dict))
                for nickname, client in client_id_socket_dict.items():
                    if nickname == clientNumber:
                        continue
                    # client[0].send(serverMessage.encode())
                    send(client[0], serverMessage)
                print("{} left. There are {} users now".format(clientNumber, len(client_id_socket_dict)))
                break
            # If a header for the command and role is received, execute the appropriate code.
            if header == MESSAGE:
                # Broadcasts the message.
                serverMessage = MESSAGE + '\n' + clientNumber + '> ' + body
                for nickname, client in client_id_socket_dict.items():
                    if nickname == clientNumber:
                        continue
                    # client[0].send(serverMessage.encode())
                    send(client[0], serverMessage)
            elif header == USERS:
                serverMessage = USERS + '\n'
                for nickname, client in client_id_socket_dict.items():
                    serverMessage += "Nickname = {}, IP = {}, Port = {} /".format(nickname, client[1][0], client[1][1])
                # connectionSocket.send(serverMessage.encode())
                send(connectionSocket, serverMessage)
            elif header == WHISPER:
                nickname, client_message = body.split(' ', maxsplit=1)
                if nickname not in client_id_socket_dict.keys():
                    serverMessage = WHISPER + '\n' + 'Cannot find the nickname'
                    # connectionSocket.send(serverMessage.encode())
                    send(connectionSocket, serverMessage)
                else:
                    serverMessage = WHISPER + '\n' + clientNumber + '(wh)> ' + client_message
                    # client_id_socket_dict[nickname][0].send(serverMessage.encode())
                    send(client_id_socket_dict[nickname][0], serverMessage)
            elif header == EXIT:
                del client_id_socket_dict[clientNumber]
                connectionSocket.close()
                serverMessage = MESSAGE + '\n' + "{} is disconnected. There are {} users in the chat room.".format(clientNumber, len(client_id_socket_dict))
                for nickname, client in client_id_socket_dict.items():
                    if nickname == clientNumber:
                        continue
                    # client[0].send(serverMessage.encode())
                    send(client[0], serverMessage)
                print("{} left. There are {} users now".format(clientNumber, len(client_id_socket_dict)))
                break
            elif header == VERSION:
                serverMessage = VERSION + '\n' + "server version: {}, client version: {}".format(server_version, client_version)
                # connectionSocket.send(serverMessage.encode())
                send(connectionSocket, serverMessage)
            elif header == RENAME:
                # If the name command has been entered, check the validation for that nickname.
                if body not in client_id_socket_dict.keys():
                    if re.match('^[a-zA-Z-]{1,32}$', body):
                        client_id_socket_dict[body] = client_id_socket_dict.pop(clientNumber)
                        clientNumber = body
                        serverMessage = RENAME + '\n' + "Nickname change is complete."
                        # connectionSocket.send(serverMessage.encode())
                        send(connectionSocket, serverMessage)
                    else:
                        serverMessage = RENAME + '\n' + "Invalid nickname."
                        # connectionSocket.send(serverMessage.encode())
                        send(connectionSocket, serverMessage)
                else:
                    serverMessage = RENAME + '\n' + 'The nickname already exists.'
                    # connectionSocket.send(serverMessage.encode())
                    send(connectionSocket, serverMessage)
            elif header == F_FILE:
                body = body.split('/', maxsplit=2)
                for nickname, client in client_id_socket_dict.items():
                    if nickname == clientNumber:
                        continue
                    if body[0] == '1':
                        serverMessage = F_FILE + '\n' + '{} is sending file {}'.format(clientNumber, body[1]) + '/' + \
                                        body[0] + '/' + body[2]
                    elif body[0] == '0':
                        serverMessage = F_FILE + '\n' + 'last {}'.format(body[1]) + '/' + body[0]
                    elif body[0] == '2':
                        serverMessage = F_FILE + '\n' + 'ing {}'.format(body[1]) + '/' + body[0] + '/' + body[2]
                    # client[0].send(serverMessage.encode())
                    send(client[0], serverMessage)
            elif header == W_FILE:
                status, nickname, filename, file_content = body.split('/', maxsplit=3)

                if status == FIRST:
                    if nickname not in client_id_socket_dict.keys():
                        serverMessage = W_FILE + '\n' + 'nickname does not exist'
                        # connectionSocket.send(serverMessage.encode())
                        send(connectionSocket, serverMessage)

                    serverMessage = W_FILE + '\n' + '{} is sending file {} to {}'.format(clientNumber, filename, nickname) + '/' + FIRST + '/' + file_content
                elif status == ING:
                    serverMessage = W_FILE + '\n' + '{} {} to {}'.format(clientNumber, filename, nickname) + '/' + ING + '/' + file_content
                elif status == LAST:
                    serverMessage = W_FILE + '\n' + '{} {} to {}'.format(clientNumber, filename, nickname) + '/' + LAST + '/' + file_content
                    nickname_flag = True
                    # client_id_socket_dict[nickname][0].send(serverMessage.encode())
                if nickname in client_id_socket_dict.keys():
                    send(client_id_socket_dict[nickname][0], serverMessage)
            elif header == RTT:
                serverMessage = RTT + '\n'
                # connectionSocket.send(serverMessage.encode())
                send(connectionSocket, serverMessage)

    except KeyboardInterrupt:
        serverSocket.close()
        exit("Bye bye~")


if __name__ == "__main__":

    try:
        # Open the server socket.
        serverSocket.bind(('', serverPort))
        serverSocket.listen(1)
        print("The server is ready to receive on port", serverPort)
        # Wait for a connection again when the client is disconnected.
        while True:
            # Connect to client..
            (connectionSocket, clientAddress) = serverSocket.accept()
            # message = connectionSocket.recv(2048)
            message = recv(connectionSocket)
            # message = message.decode()
            header, body = message.split('\n')
            # Check the number of clients currently in the chat room.
            if len(client_id_socket_dict) >= 10:
                serverMessage = FAIL + '\n' + "full. cannot connect"
                # connectionSocket.send(serverMessage.encode())
                send(connectionSocket, serverMessage)
            else:
                # Check the client's packet again.
                if not re.match('^[a-zA-Z-]{1,32}$', body):
                    serverMessage = FAIL + '\n' + "Nicknames with special characters are not allowed"
                else:
                    # If the validation passes, it creates a thread for the client.
                    if header == JOIN:
                        if body not in client_id_socket_dict.keys():
                            t = threading.Thread(target=thread, args=(connectionSocket, clientAddress, body), daemon=True)
                            t.start()
                        else:
                            serverMessage = FAIL + '\n' + 'that nickname is used by another user. cannot connect'
                            # connectionSocket.send(serverMessage.encode())
                            send(connectionSocket, serverMessage)
    # When you shut down the server, it exports the clients it belongs to.
    except KeyboardInterrupt:
        total_client = len(client_id_socket_dict) - 1
        for key, value in client_id_socket_dict.items():
            value[0].close()
            print("{} left. There are {} users now".format(key, total_client))
            total_client -= 1
        exit("Bye bye~")
    # If you are already using the server's port, it will be an error.
    except OSError:
        exit("Address already in use")

    except Exception as e:
        print("Bye bye~")
        exit("error")

    finally:
        serverSocket.close()

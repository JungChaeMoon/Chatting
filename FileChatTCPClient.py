#
#
# FileChatTCPClient.py
# 20151631 Jung Chaemoon
#

from socket import *
import sys
import re
import time
import threading
import base64

serverName = '127.0.0.1'
serverPort = 21631

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
flag = True
file_name_flag = True
start = 0
end = 0
remain = ''

# Because tcp works in the stream, it created a layer to use message protocol.
def send(clientSocket, message):
    escape = '<semicolon>'
    message = message.replace(';', escape)
    message = message + ';'
    clientSocket.send(message.encode())


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


# Send Only Threads
def send_message_thread():
    global clientSocket, start, flag

    try:
        while True:
            option = input()
            flag = True
            # If the command is initially included, check the validation of the command, and if the validation check passes
            # create a packet and send it to the server.
            if option.startswith('\\users'):
                if len(option.split(' ', maxsplit=1)) > 1:
                    print('Invalid command.')
                    continue
                message = USERS + '\n'
            elif option.startswith('\\wh'):
                if len(option.split(' ', maxsplit=2)) < 3:
                    print('Invalid command')
                    continue
                option = option.split(' ')
                message = WHISPER + '\n' + option[1] + ' ' + ' '.join(option[2:])
            elif option.startswith('\\exit'):
                if len(option.split(' ', maxsplit=1)) > 1:
                    print('Invalid command.')
                    continue
                message = EXIT + '\n'
            elif option.startswith('\\version'):
                if len(option.split(' ', maxsplit=1)) > 1:
                    print('Invalid command.')
                    continue
                message = VERSION + '\n'
            elif option.startswith('\\rename'):
                if len(option.split(' ')) != 2:
                    print('Invalid command.')
                    continue
                option = option.split(' ')
                message = RENAME + '\n' + option[1]
            elif option.startswith('\\rtt'):
                if len(option.split(' ', maxsplit=1)) > 1:
                    print('Invalid command.')
                    continue
                message = RTT + '\n'
            elif option.startswith('\\fsend'):
                flag = False
                if len(option.split(' ')) != 2:
                    print('Invalid command.')
                    continue
                option = option.split(' ')
                file_name = option[1]
                message = ''
                try:
                    # I did the framing.
                    with open(file_name, 'rb') as f:
                        l = f.read(1024)
                        base64_l = base64.b64encode(l)
                        message = F_FILE + '\n' + FIRST + '/' + file_name + '/' + base64_l.decode('ascii')
                        send(clientSocket, message)
                        while True:
                            l = f.read(1024)
                            if not l:
                                message = F_FILE + '\n' + LAST + '/' + file_name + '/' + 'last'

                                send(clientSocket, message)
                                break
                            else:
                                base64_l = base64.b64encode(l)
                                message = F_FILE + '\n' + ING + '/' + file_name + '/' + base64_l.decode('ascii')
                                send(clientSocket, message)
                except FileNotFoundError:
                    print("file does not exist")
                    continue
            elif option.startswith('\\wsend'):
                flag = False
                if len(option.split(' ')) != 3:
                    print('Invalid command')
                    continue
                option = option.split(' ')
                send_nickname = option[2]
                file_name = option[1]
                message = ''
                try:
                    with open(file_name, 'rb') as f:
                        l = f.read(2048)
                        base64_l = base64.b64encode(l)
                        message = W_FILE + '\n' + FIRST + '/' + send_nickname + '/' + file_name + '/' + base64_l.decode('ascii')
                        send(clientSocket, message)
                        while True:
                            l = f.read(2048)
                            if not l:
                                message = W_FILE + '\n' + LAST + '/' + send_nickname + '/' + file_name + '/' + 'last'
                                send(clientSocket, message)
                                break
                            else:
                                base64_l = base64.b64encode(l)
                                message = W_FILE + '\n' + ING + '/' + send_nickname + '/' + file_name + '/' + base64_l.decode('ascii')
                                send(clientSocket, message)

                except FileNotFoundError:
                    print("file does not exist")
                    continue
            else:
                message = MESSAGE + '\n' + option

            # Time measurement using a time function to measure round trip response time
            start = time.time()
            if flag:
                # clientSocket.send(message.encode())
                send(clientSocket, message)
            # While sending a message to the server and waiting for a response, the server may have a problem.
            if serverMessage == '':
                raise ConnectionError

        # Shutdown socket when control-c is pressed
    except KeyboardInterrupt:
        send(clientSocket, EXIT+'\n')

    except Exception as e:
        clientSocket.close()

        # The server can shut down after the client starts. Returns the error when writing to the terminated socket.
    except BrokenPipeError:
        clientSocket.close()
        exit("Server connect refused")

        # Connection error with the server may occur.
    except ConnectionError:
        clientSocket.close()
        exit("Server connect refused")

    except IndexError:
        clientSocket.close()
        exit("Please enter the nickname")


if __name__ == "__main__":

    clientSocket = socket(AF_INET, SOCK_STREAM)

    try:
        file_name = ''
        # This is the part to check right format for nicknames.
        nickName = sys.argv[1]
        if not re.match('^[a-zA-Z-]{1,32}$', nickName):
            print("Invalid nickname.")
            raise Exception
        # The code that connects the server to the socket
        clientSocket.connect((serverName, serverPort))

        # If it pass, It will send a nickname to the server and check the duplication and the validation again.
        message = JOIN + '\n' + nickName
        send(clientSocket, message)
        # serverMessage = clientSocket.recv(2048)
        # serverMessage = serverMessage.decode()
        serverMessage = recv(clientSocket)
        header, body = serverMessage.split('\n')
        # Create a dedicated thread to send if the server passes the validation for the nickname.
        if header == SUCCESS:
            print(body)
            send_t = threading.Thread(target=send_message_thread, daemon=True)
            send_t.start()
        # Code for failure.
        elif header == FAIL:
            print(body)
            clientSocket.close()
            exit()

        try:
            # This is a dedicated main thread that only receive.
            while True:
                # serverMessage = clientSocket.recv(2048)
                # end = time.time()
                # serverMessage = serverMessage.decode()
                serverMessage = recv(clientSocket)

                # If the server sends an empty string, consider it a connection error
                if serverMessage == '':
                    raise ConnectionError

                # This is where packets from the server are separated into headers and body parts.
                header, body = serverMessage.split('\n', maxsplit=1)

                # This is the part that prints out each header.
                if header == MESSAGE:
                    print(body)
                elif header == USERS:
                    for user in body.split('/'):
                        print(user)
                elif header == WHISPER:
                    print(body)
                elif header == EXIT:
                    print(body)
                elif header == VERSION:
                    print(body)
                elif header == RENAME:
                    print(body)
                elif header == RTT:
                    print('Response time: {}ms'.format(round((end - start) * 1000, 2)))
                elif header == F_FILE:
                    body = body.split('/', maxsplit=1)
                    status = body[1].split('/', maxsplit=1)
                    if status[0] == FIRST:
                        print(body[0])
                        file_name = 'fsend' + '_' + body[0].split(' ')[0] + '_' + nickName + '_' + body[0].split(' ')[
                            -1]
                        with open(file_name, 'wb') as f:
                            f.write(base64.b64decode(status[1]))

                    elif status[0] == ING:
                        with open(file_name, 'ab') as f:
                            f.write(base64.b64decode(status[1]))
                    elif status[0] == LAST:
                        print("file {} received from {}".format(file_name, nickName))
                        continue

                elif header == W_FILE:
                    body = body.split('/', maxsplit=1)
                    if len(body) == 1:
                        print(body[0])
                        continue


                    file_name = 'wsend' + '_' + body[0].split(' ')[0] + '_' + nickName + '_' + body[0].split(' ')[-3]
                    if body[1].split('/')[0] == FIRST:
                        print(body[0])
                        with open(file_name, 'wb') as f:
                            f.write(base64.b64decode(body[1].split('/', maxsplit=1)[1]))

                    elif body[1].split('/')[0] == ING:
                        with open(file_name, 'ab') as f:
                            f.write(base64.b64decode(body[1].split('/', maxsplit=1)[1]))

                    elif body[1].split('/')[0] == LAST:
                        print("file {} received from {}".format(file_name, nickName))
                        continue

        except ConnectionError as e:
            clientSocket.close()
            print('adios~')

    # Shutdown socket when control-c is pressed
    except KeyboardInterrupt:
        send(clientSocket, EXIT + '\n')

    except IndexError as e:
        print(e)
        clientSocket.close()
        exit("Please enter the nickname")

    except Exception as e:
        print(e)
        clientSocket.close()
        exit('server connect refused')

    # The server can shut down after the client starts. Returns the error when writing to the terminated socket.
    except BrokenPipeError as e:
        print(e)
        clientSocket.close()
        exit("Server connect refused")

    # Connection error with the server may occur.
    except ConnectionError as e:
        print(e)
        clientSocket.close()
        exit("Server connect refused")

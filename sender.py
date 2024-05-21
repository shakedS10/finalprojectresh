import argparse
import socket
import ssl
import os
import random
import string
import packet
import threading


totalsize = 1024 * 1024 * 10


def create_random_text_file(filename, size_in_bytes):
    # Characters to choose from
    chars = string.ascii_letters + string.digits + ' \n'

    # Open file in write mode
    with open(filename, 'w') as f:
        while os.path.getsize(filename) < size_in_bytes:
            # Generate a random string
            random_text = ''.join(random.choices(chars, k=1024))
            f.write(random_text)
            f.flush()  # Ensure content is written to the file

        # Ensure the file is exactly the desired size
        current_size = os.path.getsize(filename)
        if current_size > size_in_bytes:
            with open(filename, 'r+') as f:
                f.truncate(size_in_bytes)


def read_file_to_string(filename):
    with open(filename, 'r') as file:
        content = file.read()
    return content


# QUIC Client

def create_connection(host, port, stream_id, packet_size, filesize, data):
    # Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Send a connection request packet
    long_header_packet = packet.LongHeader('0', stream_id, '1')  # SYN packet
    sock.sendto(long_header_packet.encode().encode(), (host, port))
    # Receive the response packet
    response_data, addr = sock.recvfrom(1024)
    response_packet = packet.LongHeader('', '', '')
    response_packet.decode(response_data.decode())
    print(response_packet.con_id, response_packet.t)
    if response_packet.t == '0':
        print("Connection established.")
        threading.Thread(target=send_data,
                         args=(sock, host, port, response_packet.con_id, packet_size, filesize, data)).start()
    else:
        print("Connection failed.")
        exit(1)


def send_data(sock, host, port, con_id, packet_size, filesize, data):
    # Send data packets
    frame = 0
    total_bytes_sent = 0

    while total_bytes_sent < filesize:
        # Create a data packet

        data_packet = packet.ShortHeader(0, con_id, frame, data[frame * packet_size:(frame + 1) * packet_size], filesize, packet_size)
        # Send the data packet
        sock.sendto(data_packet.encode().encode(), (host, port))
        print(data_packet.encode().encode())
        total_bytes_sent += packet_size
        frame += 1
    term_pac = packet.LongHeader(0, con_id, '2')  # TERMINATE packet
    print("Sending terminate packet")
    sock.sendto(term_pac.encode().encode(), (host, port))



# Usage example
if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="A Calculator Client.")

    arg_parser.add_argument("-p", "--port", type=int,
                            default="11000", help="The port to connect to.")
    arg_parser.add_argument("-ip", "--ip", type=str,
                            default="127.0.0.2", help="The host to connect to.")

    packet_size1 = random.randint(1000, 2000)
    packet_size2 = random.randint(1000, 2000)
    file_size_limit = 10000
    filename = "random.txt"
    filesize = random.randint(1000, 10000) * 1000
    create_random_text_file(filename, filesize)
    data = read_file_to_string(filename)

    # Start sending on multiple streams with different packet sizes
    threading.Thread(target=create_connection,
                     args=('127.0.0.1', 9999, '1', packet_size1, file_size_limit, data[0:len(data) // 4])).start()
    len2 = len(data) // 4 * 2
    len3 = len(data) // 4 * 3
    threading.Thread(target=create_connection,
                     args=('127.0.0.1', 9999, '2', packet_size2, file_size_limit, data[len(data)//4:len2])).start()
    threading.Thread(target=create_connection,
                     args=('127.0.0.1', 9999, '3', packet_size1, file_size_limit, data[len2:len3])).start()
    threading.Thread(target=create_connection,
                     args=('127.0.0.1', 9999, '4', packet_size2, file_size_limit, data[len3:])).start()

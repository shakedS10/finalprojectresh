import argparse
import socket
import os
import random
import string
import time
import packet
import threading
import constants as c

active_connections = {}


def create_random_text_file(filename, size_in_bytes):
    # Characters to choose from
    chars = string.ascii_letters + string.digits + ' \n'

    # Open file in write mode
    with open(filename, 'w') as f:
        while os.path.getsize(filename) < size_in_bytes:
            # Generate a random string
            random_text = ''.join(random.choices(chars, k=c.randomSeed))
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


def send_data(sock, host, port, con_id, packet_size, filesize, data):
    # Send data packets
    frame = 0
    total_bytes_sent = 0
    print(f"Sending data from thread {con_id}")
    while total_bytes_sent < filesize:
        # Create a data packet
        data_packet = packet.ShortHeader(0, con_id, frame, data[frame * packet_size:(frame + 1) * packet_size],
                                         filesize, packet_size)
        # Send the data packet
        sock.sendto(data_packet.encode().encode(), (host, port))

        total_bytes_sent += packet_size
        frame += 1
        time.sleep(delay)


def start_sender(host, port):
    packet_size1 = random.randint(c.packetSizeMin, c.packetSizeMax)
    filename = "random.txt"
    global filesize
    filesize = random.randint(c.fileSizeMin, c.fileSizeMax) * c.scaleToMB
    create_random_text_file(filename, filesize)
    data = read_file_to_string(filename)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    long_header_packet = packet.LongHeader('0', '-1', '1')  # SYN packet
    sock.sendto(long_header_packet.encode().encode(), (host, port))

    response_data, addr = sock.recvfrom(c.senderReceivedSize)
    response_packet = packet.LongHeader('', '', '')
    response_packet.decode(response_data.decode())
    print(response_packet.con_id, response_packet.t)
    if response_packet.t == '0':
        print("Connection established.")
        threads = []
        dlen = len(data) // tcount
        for i in range(tcount):
            threads.append(threading.Thread(target=send_data,
                                            args=(sock, host, port, str(i + 1), packet_size1, dlen,
                                                  data[i * dlen:(i + 1) * dlen])))

        # Start all threads
        for thread in threads:
            thread.start()
            time.sleep(delay)

        # Wait for all threads to finish
        for thread in threads:
            thread.join()

        term_pac = packet.LongHeader(0, '-1', '2')  # TERMINATE packet
        print("Sending terminate packet")
        sock.sendto(term_pac.encode().encode(), (host, port))
        sock.close()
    else:
        print("Connection failed.")
        exit(1)


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="A Receiver for QUIC-like packets.")
    arg_parser.add_argument("-p", "--port", type=int, default=c.defaultPort, help="The port to listen on.")
    arg_parser.add_argument("-ip", "--ip", type=str, default=c.defaultIP, help="The host to listen on.")
    arg_parser.add_argument("-t", "--t", type=int, default=c.defaultStreamNumber, help="amount of threads")
    arg_parser.add_argument("-o", "--output", type=str, default="output.txt", help="The output file name.")
    arg_parser.add_argument("-s", "--sleep", type=float, default=c.defaultDelay, help="delay for packets")
    ip = arg_parser.parse_args().ip
    port = arg_parser.parse_args().port
    global output
    output = arg_parser.parse_args().output
    global tcount
    tcount = arg_parser.parse_args().t
    global delay
    delay = arg_parser.parse_args().sleep

    start_sender(ip, port)

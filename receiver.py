import argparse
import socket
import threading
import os
from collections import defaultdict
import packet  # Assuming the packet module is available and correctly implemented

# Constants
TERMINATE_MSG = "TERMINATE"
ACK_DELAY = 0.1  # ACK delay in seconds
terminate_flag = threading.Event()
active_connections = set()

# Data structures to track received data and stats
stats = defaultdict(lambda: {'bytes_received': 0, 'packets_received': 0})
received_data = defaultdict(lambda: bytearray())
expected_frames = defaultdict(int)


# Function to send ACK packet
def send_ack(sock, host, port, con_id):
    ack_packet = packet.LongHeader('0', con_id, '0')  # ACK packet
    sock.sendto(ack_packet.encode().encode(), (host, port))
    print(f"Sent ACK Packet for Connection {con_id}")


# Function to handle SYN packet
# Function to handle SYN packet
# Function to handle SYN packet
def handle_syn(packet_data, sock, host, port):
    pac = packet.LongHeader(flags='', con_id='', t='')
    pac.decode(packet_data)
    if pac.t == '2':
        print(f"Received TERMINATE for Connection {pac.con_id}")
        return handle_term(pac.con_id)
    print(f"Received SYN for Connection {pac.con_id}")
    expected_frames[pac.con_id] = 0
    active_connections.add(pac.con_id)
    send_ack(sock, host, port, pac.con_id)


def handle_term(con_id):
    terminate_flag.set()
    return TERMINATE_MSG


# Function to handle data packet
def handle_data(packet_data, sock, host, port):
    pac = packet.ShortHeader(flags='', con_id='', seq='', data='', filesize='', packet_size='')
    pac.decode(packet_data)
    print(f"Received Data Packet for Connection {pac.con_id}, Frame {pac.seq}")
    update_stats(pac.con_id, len(packet_data))
    received_data[pac.con_id] += pac.data.encode()
    expected_frames[pac.con_id] += 1

    # Check if this is the last expected packet
    if expected_frames[pac.con_id] * pac.packet_size >= pac.filesize:
        send_ack(sock, host, port, pac.con_id)


# Function to update statistics
def update_stats(con_id, payload_size):
    global stats
    stats[con_id]['bytes_received'] += payload_size
    stats[con_id]['packets_received'] += 1


# Function to print statistics
def print_stats():
    global stats
    print("Receiver Statistics:")
    for con_id, data in stats.items():
        print(f"Connection {con_id}:")
        print(f"  Total Bytes Received: {data['bytes_received']}")
        print(f"  Total Packets Received: {data['packets_received']}")


# Function to save received data to files
def save_received_data():
    for con_id, data in received_data.items():
        filename = f"received_{con_id}.txt"
        with open(filename, 'wb') as f:
            f.write(data)
        print(f"Data for Connection {con_id} saved to {filename}")
    with open(output, 'wb') as f:
        for con_id, data in received_data.items():
            f.write(data)
        print(f"Data for Connection saved to {output}")


# Function to handle each stream separately
def handle_stream(sock, host, port):
    while True:
        try:
            data, addr = sock.recvfrom(65535)  # Adjust buffer size here
            print(data)
            if data.startswith(b"L"):
                if handle_syn(data.decode(), sock, addr[0], addr[1]) == TERMINATE_MSG:
                    break
            elif data.startswith(b"S"):
                handle_data(data.decode(), sock, addr[0], addr[1])
        except socket.timeout:
            print("Socket timeout.")
            break


# Function to start the receiver
def start_receiver(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    sock.settimeout(5.0)  # Add a timeout to handle termination gracefully
    print(f"Receiver started on {host}:{port}")

    handle_stream(sock, host, port)

    print_stats()
    save_received_data()
    sock.close()


# Main function to start the receiver
if __name__ == "__main__":
    # Start the receiver
    arg_parser = argparse.ArgumentParser(description="A Receiver for QUIC-like packets.")
    arg_parser.add_argument("-p", "--port", type=int, default=9999, help="The port to listen on.")
    arg_parser.add_argument("-ip", "--ip", type=str, default="127.0.0.1", help="The host to listen on.")
    arg_parser.add_argument("-o", "--output", type=str, default="output.txt", help="The output file name.")

    ip = arg_parser.parse_args().ip
    port = arg_parser.parse_args().port
    global output
    output = arg_parser.parse_args().output
    start_receiver(ip, port)


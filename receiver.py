import socket
import threading
import time
from collections import defaultdict

# Constants
TERMINATE_MSG = "TERMINATE"
ACK_DELAY = 0.1  # ACK delay in seconds
stats = defaultdict(lambda: {'bytes_received': 0, 'packets_received': 0})


def send_terminate_message(sock, host, port):
    global terminate_flag
    terminate_flag = True
    sock.sendto(TERMINATE_MSG.encode(), (host, port))
    print("Sent terminate message")


def send_ack(sock, host, port, stream_id):
    ack_packet = f"ACK:{stream_id}"
    sock.sendto(ack_packet.encode(), (host, port))
    print(f"Sent ACK Packet for Stream {stream_id}")


def handle_long_header(packet, sock, host, port):
    parts = packet.split(':')
    if len(parts) >= 2:
        stream_id_part = parts[1].split('=')
        if len(stream_id_part) >= 2:
            stream_id = stream_id_part[1]
            print(f"Received Long Header for Stream {stream_id}")
            send_ack(sock, host, port, stream_id)
            update_stats(stream_id, len(packet))
        else:
            print("Malformed stream ID in long header:", parts)
    else:
        print("Malformed long header:", packet)
    print("Received packet:", packet)


def handle_short_header(packet, sock, host, port):
    parts = packet.split(':')
    stream_id = parts[1]
    print(f"Received Short Header for Stream {stream_id}")
    send_ack(sock, host, port, stream_id)
    update_stats(stream_id, len(packet))


def handle_syn_packet(sock, host, port, stream_id):
    ack_packet = f"ACK:SYN"
    sock.sendto(ack_packet.encode(), (host, port))
    print(f"Sent ACK for SYN packet on Stream {stream_id}")


def update_stats(stream_id, payload_size):
    global stats
    stats[stream_id]['bytes_received'] += payload_size
    stats[stream_id]['packets_received'] += 1


def print_stats():
    global stats
    print("Receiver Statistics:")
    for stream_id, data in stats.items():
        print(f"Stream {stream_id}:")
        print(f"  Total Bytes Received: {data['bytes_received']}")
        print(f"  Total Packets Received: {data['packets_received']}")


def start_receiver(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)  # Set receive buffer size
    print(f"Receiver started on {host}:{port}")

    while True:
        try:
            data, addr = sock.recvfrom(4096)  # Adjust buffer size here
            packet = data.decode()
            if packet.startswith("SYN:"):
                handle_syn_packet(sock, addr[0], addr[1], packet.split('=')[1].split(':')[0])
            elif packet.startswith("LSYN:"):
                handle_syn_packet(sock, addr[0], addr[1], packet.split('=')[1].split(':')[0])
            elif packet.startswith("S"):
                handle_short_header(packet, sock, addr[0], addr[1])
            elif packet.startswith("L"):
                handle_long_header(packet, sock, addr[0], addr[1])
            elif packet == TERMINATE_MSG:
                print("Termination signal received. Exiting...")
                break
        except socket.timeout:
            print("Socket timeout.")
    print_stats()
    sock.close()


if __name__ == "__main__":
    # Start the receiver
    threading.Thread(target=start_receiver, args=('127.0.0.1', 9999)).start()
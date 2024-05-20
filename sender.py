import argparse
import socket
import ssl
import os
import packet
import threading

packet_size = 1024
totalsize = 1024 * 1024 * 10
# QUIC Client

def create_connection(host, port, stream_id, packet_size, filesize, data):
        # Create a UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Send a connection request packet
    pac = packet.LongHeader(stream_id, 1)
    sock.sendto(pac.encode().encode(), (host, port))
    # Receive the response packet
    data, addr = sock.recvfrom(1024)
    response_packet = packet.LongHeader.decode(data.decode())
    if response_packet.t == 0:
        print("Connection established.")
        threading.Thread(target=send_data, args=(sock,host,port,response_packet.con_id,packet_size,filesize, data)).start()
    else:
        print("Connection failed.")
        exit(1)



def send_data(sock,host,port,con_id,packet_size,filesize, data):

    # Send data packets
    frame = 0
    total_bytes_sent = 0

    while total_bytes_sent < totalsize:
        # Create a data packet

        data_packet = packet.ShortHeader(0, con_id, frame, data[frame*packet_size:(frame+1)*packet_size])
        # Send the data packet
        sock.sendto(data_packet.encode().encode(), (host, port))
        total_bytes_sent += packet_size
        frame += 1
    term_pac = packet.LongHeader(con_id, 2)
    sock.sendto(term_pac.encode().encode(), (host, port))
    # Wrap the socket for TLS

# Usage example
if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="A Calculator Client.")

    arg_parser.add_argument("-p", "--port", type=int,
                            default="11000", help="The port to connect to.")
    arg_parser.add_argument("-ip", "--ip", type=str,
                            default="127.0.0.2", help="The host to connect to.")

    args = arg_parser.parse_args()

    ip = args.ip
    port = args.port
    server = QUICClient(('127.0.0.1', 10000))
    server.send_packet(b"Hello, Server!")

#
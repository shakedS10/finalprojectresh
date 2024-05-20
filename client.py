import argparse
import socket
import ssl
import os
import packet


# QUIC Client
class QUICClient:
    def __init__(self, server_address):
        self.server_address = server_address
        self.connection_id = os.urandom(8).hex()
        self.packet_number = 0
        self.context = ssl.create_default_context()

    def send_packet(self, payload):
        pac = packet.quicpacket(self.connection_id, self.packet_number, payload)
        self.packet_number += 1

        # Create a UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Wrap the socket for TLS
        tls_sock = self.context.wrap_socket(sock, server_hostname=self.server_address[0])

        # Send the packet
        tls_sock.sendto(pac.encode(), self.server_address)

        # Close the socket
        tls_sock.close()

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


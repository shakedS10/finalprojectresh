class quicheader:
    def __init__(self, flags, id , num):
        self.flags = flags
        self.id = id
        self.num = num

#
class quicdata:
    def __init__(self, data , streamid , datalen):
        self.data = data
        self.streamid = streamid
        self.datalen = datalen


class quicpacket:
    def __init__(self, header, data):
        self.header = header
        self.data = data

    def encode(self):
        return f"{self.connection_id}|{self.packet_number}|{self.payload}".encode()

    @staticmethod
    def decode(data):
        parts = data.decode().split("|")
        return quicpacket(parts[0], int(parts[1]), parts[2])


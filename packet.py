class LongHeader:
    def __init__(self, flags, con_id, t):
        self.con_id = con_id
        self.t = t  #0-ACK, 1-SYN 2-TERMINATE
        self.flags = flags

    def encode(self):
        code = f"L{self.flags}:{self.con_id}:{self.t}"
        return code

    def decode(self, data):
        self.flags, self.con_id, self.t = data.split(':')
        return self


class ShortHeader:
    def __init__(self, flags, con_id, seq, data, filesize, packet_size):
        self.flags = flags
        self.con_id = con_id
        self.seq = seq
        self.data = data
        self.filesize = filesize
        self.packet_size = packet_size

    def encode(self):
        code = f"S{self.flags}:{self.con_id}:{self.seq}:{self.data}:{self.filesize}:{self.packet_size}"
        return code

    def decode(self, data):
        parts = data.split(":")
        if len(parts) == 6:
            self.flags, self.con_id, self.seq, self.data, self.filesize, self.packet_size = parts
        else:
            print("Invalid data format")

class LongHeader:
    def __init__(self, con_id, t):
        self.con_id = con_id
        self.t = t  #0-ACK, 1-SYN 2-TERMINATE

    def encode(self):
        return self.con_id + ":" + self.t

    def decode(self, data):
        self.con_id, self.t = data.split(":")
        return self


class ShortHeader:
    def __init__(self, flags, con_id, seq, data):
        self.flags = flags
        self.con_id = con_id
        self.seq = seq
        self.data = data

    def encode(self):
        return self.flags + ":" + self.con_id + ":" + self.seq + ":" + self.data

    def decode(self, data):
        self.flags, self.con_id, self.seq, self.data = data.split(":")
        return self

class SMBus():

    def __init__(self, bus_number: int):
        self.bus_number = bus_number
        self.fake_register_output = 0

    def i2c_rdwr(self, write, read=None):
        self.fake_register_input = write
        if read is not None:
            read.clear()
            read.extend(self.fake_register_output)

    def fakeInput(self):
        return self.fake_register_input


class i2c_msg():

    def write(address, command):
        return [address, command]

    def read(offset, length):
        return [offset, length]

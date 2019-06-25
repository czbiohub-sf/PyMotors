import unittest
from unittest.mock import patch
import warnings
import pymotors
import tests.fake_smbus2 as fake_smbus2


class TicI2c_Utilities(unittest.TestCase):

    @patch.object(pymotors.tic_stepper.TicI2C, '__init__', return_value=None)
    def setUp(self, mockInit):
        self.stepper = pymotors.tic_stepper.TicI2C(3, 14)
        self.stepper.bus = fake_smbus2.SMBus(3)
        self.stepper.address = 14

    def test_fake_quick_send(self):
        output = self.stepper.send([0x99, 'quick'])
        self.assertEqual(None, output)

    def test_fake_7bit_send(self):
        payload = 124
        output = self.stepper.send([0xAA, 7], payload)
        self.assertEqual(None, output)

    def test_data_larger_than_7_bit(self):
        payload = 1024
        try:
            warned = 0
            self.stepper.send([0xAA, 7], payload)
        except ValueError:
            warned = 1
        self.assertEqual(1, warned)

    def test_fake_32bit_send(self):
        payload = 2147483647
        output = self.stepper.send([0xBB, 32], payload)
        self.assertEqual(None, output)

    @patch('pymotors.tic_stepper.i2c_msg', new=fake_smbus2.i2c_msg)
    def test_fake_read(self):
        self.stepper.send([0x00, 'quick'])  # purge native i2c_msg
        self.stepper.bus.fake_register_output = [1, 2, 3, 4, 5, 6, 7, 8]
        read_bits = 8
        payload = [0x33, read_bits]
        output = self.stepper.send([0xCC, 'read'], payload)
        self.assertEqual(self.stepper.bus.fake_register_output, output)

    @patch('pymotors.tic_stepper.i2c_msg')
    def test_fake_32_processing(self, mockI2c):
        mockI2c.write = fake_smbus2.i2c_msg.write
        payload = 0x7FFFFFFF
        offset = 0xBB
        address = self.stepper.address
        self.stepper.send([offset, 32], payload)
        input = self.stepper.bus.fakeInput()
        self.assertEqual([address, [offset, 0xFF, 0xFF, 0xFF, 0x7F]], input)


class TicSerial_Utilities(unittest.TestCase):
    @patch('pymotors.tic_stepper.serial')
    def setUp(self, MockSerial):
        port_name = '/dev/ttyacm0'
        baud_rate = 9600
        port = pymotors.tic_stepper.serial.Serial(port_name, baud_rate,
                                             timeout=0.1, write_timeout=0.1)
        device_number = 14
        self.stepper = pymotors.tic_stepper.TicSerial(port, device_number)

    def test_make_serial_input_without_device_number_and_data(self):
        offset = 0x5A
        self.stepper.device_number = None
        serial_input = self.stepper._makeSerialInput(offset)
        expected_input = bytes([offset])
        self.assertEqual(expected_input, serial_input)

    def test_make_serial_input_with_device_number_and_no_data(self):
        offset = 0x5A
        serial_input = self.stepper._makeSerialInput(offset)
        expected_input = bytes([0xAA,
                                self.stepper.device_number,
                                offset & 0x7F])
        self.assertEqual(expected_input, serial_input)

    def test_make_serial_input_with_device_number_and_data(self):
        offset = 0x5A
        data = [123]
        serial_input = self.stepper._makeSerialInput(offset, data)
        expected_input = bytes([0xAA, self.stepper.device_number,
                                offset & 0x7F] + data)
        self.assertEqual(expected_input, serial_input)

    def test_quick_send(self):
        operation = pymotors.tic_stepper.TicStepper.command_dict['energize']
        self.stepper.send(operation)
        expected = self.stepper._makeSerialInput(operation[0])
        self.stepper.port.write.assert_called_with(expected)

    def test_7bit_send(self):
        operation = pymotors.tic_stepper.TicStepper.command_dict['goHome']
        data = 123
        self.stepper.send(operation, data)
        expected = self.stepper._makeSerialInput(operation[0], [data])
        self.stepper.port.write.assert_called_with(expected)

    def test_32bit_send(self):
        operation = pymotors.tic_stepper.TicStepper.command_dict['sMaxSpeed']
        data = 123456
        self.stepper.send(operation, data)
        data_formatting = split32BitSer(data)
        expected = self.stepper._makeSerialInput(operation[0], data_formatting)
        self.stepper.port.write.assert_called_with(expected)

    def test_data_larger_than_7_bit(self):
        operation = pymotors.tic_stepper.TicStepper.command_dict['goHome']
        data = 1234
        try:
            warned = 0
            self.stepper.send(operation, data)
        except ValueError:
            warned = 1
        self.assertEqual(True, warned)

    def test_read(self):
        operation = pymotors.tic_stepper.TicStepper.command_dict['gVariable']
        variable = pymotors.tic_stepper.TicStepper.variable_dict['max_speed']
        self.stepper.port.read.return_value = [1] * variable[1]
        self.stepper.send(operation, variable)
        expected_write = self.stepper._makeSerialInput(operation[0], [variable[0]])
        self.stepper.port.write.assert_called_with(expected_write)
        self.stepper.port.read.assert_called_with(variable[1])


class TicStepper_I2c(unittest.TestCase):
    @patch('pymotors.tic_stepper.i2c_msg', new=fake_smbus2.i2c_msg)
    @patch('pymotors.tic_stepper.SMBus', new=fake_smbus2.SMBus)
    def setUp(self):
        warnings.filterwarnings('ignore')
        self.tic = pymotors.tic_stepper.TicStepper('I2C', 3, 14)
        warnings.filterwarnings('error')

    @patch('pymotors.tic_stepper.i2c_msg', new=fake_smbus2.i2c_msg)
    def test_set_microstep(self):
        self.tic.microsteps = 1/8
        input = self.tic.com.bus.fakeInput()
        self.assertEqual([self.tic.command_dict['sStepMode'][0], 3], input[1])
        micros = self.tic.microsteps
        self.assertEqual(1/8, micros)
        self.tic.microsteps = 1/4
        input = self.tic.com.bus.fakeInput()
        self.assertEqual([self.tic.command_dict['sStepMode'][0], 2], input[1])
        self.tic.microsteps = 1/2
        input = self.tic.com.bus.fakeInput()
        self.assertEqual([self.tic.command_dict['sStepMode'][0], 1], input[1])
        self.tic.microsteps = 1
        input = self.tic.com.bus.fakeInput()
        self.assertEqual([self.tic.command_dict['sStepMode'][0], 0], input[1])
        try:
            warned = False
            self.tic.microsteps = 1/6
            input = self.tic.com.bus.fakeInput()
        except UserWarning:
            warned = True
        self.assertEqual(True, warned)

    @patch('pymotors.tic_stepper.i2c_msg', new=fake_smbus2.i2c_msg)
    def test_steps_per_second(self):
        self.tic.steps_per_second = .01
        input = self.tic.com.bus.fakeInput()
        split_input = split32BitI2c(self.tic.steps_per_second * 10000)
        self.assertEqual([self.tic.command_dict['sMaxSpeed'][0]] + split_input[:], input[1])

    @patch('pymotors.tic_stepper.i2c_msg', new=fake_smbus2.i2c_msg)
    def test_enabled(self):
        self.tic.enabled = True
        input = self.tic.com.bus.fakeInput()
        self.assertEqual(self.tic.command_dict['exitSafeStart'][0], input[1])
        self.assertEqual(True, self.tic.enabled)
        self.tic.enabled = False
        input = self.tic.com.bus.fakeInput()
        self.assertEqual(self.tic.command_dict['deenergize'][0], input[1])
        self.assertEqual(False, self.tic.enabled)

    @patch('pymotors.tic_stepper.i2c_msg', new=fake_smbus2.i2c_msg)
    def test_move(self):
        self.tic.enabled = True
        self.tic.moveAbsSteps(1000)
        input = self.tic.com.bus.fakeInput()
        split_input = split32BitI2c(1000)
        self.assertEqual([self.tic.command_dict['sTargetPosition'][0]] + split_input, input[1])

    @patch('pymotors.tic_stepper.i2c_msg', new=fake_smbus2.i2c_msg)
    def test_is_homed(self):
        not_home = [1, 1, 1, 1, 1, 1, 1, 1]
        self.tic.com.bus.fake_register_output = not_home
        check_home = self.tic.isHomed()
        input = self.tic.com.bus.fakeInput()
        self.assertEqual([self.tic.command_dict['gVariable'][0], self.tic.variable_dict['misc_flags1'][0]], input[1])
        self.assertEqual(False, check_home)
        is_home = [1, 0, 1, 1, 1, 1, 1, 1]
        self.tic.com.bus.fake_register_output = is_home
        check_home = self.tic.isHomed()
        self.assertEqual(True, check_home)


class TicStepper_Ser(unittest.TestCase):
    @patch('pymotors.tic_stepper.serial')
    def setUp(self, MockSerial):
        warnings.filterwarnings('ignore')
        port_name = '/dev/ttyacm0'
        baud_rate = 9600
        port_params = [port_name, baud_rate]
        address = 14
        self.tic = pymotors.tic_stepper.TicStepper('ser', port_params, address)
        self.write = self.tic.com.port.write
        self.read = self.tic.com.port.read
        self.cmd = self.tic.command_dict
        self.var = self.tic.variable_dict
        self.proc = self.tic.com._makeSerialInput
        warnings.filterwarnings('error')

    def test_set_microstep(self):
        operation = self.cmd['sStepMode']
        self.tic.microsteps = 1/8
        input = self.proc(operation[0], [3])
        self.write.assert_called_with(input)
        micros = self.tic.microsteps
        self.assertEqual(1/8, micros)
        self.tic.microsteps = 1/4
        input = self.proc(operation[0], [2])
        self.write.assert_called_with(input)
        self.tic.microsteps = 1/2
        input = self.proc(operation[0], [1])
        self.write.assert_called_with(input)
        self.tic.microsteps = 1
        input = self.proc(operation[0], [0])
        self.write.assert_called_with(input)
        try:
            warned = False
            self.tic.microsteps = 1/6
        except UserWarning:
            warned = True
        self.assertEqual(True, warned)

    def test_steps_per_second(self):
        operation = self.cmd['sMaxSpeed']
        data = .01
        self.tic.steps_per_second = data
        split_input = split32BitSer(data * 10000)
        input = self.proc(operation[0], split_input)
        self.write.assert_called_with(input)

    def test_enabled(self):
        operation = self.cmd['exitSafeStart']
        self.tic.enabled = True
        input = self.proc(operation[0])
        self.write.assert_called_with(input)
        self.assertEqual(True, self.tic.enabled)
        self.tic.enabled = False
        operation = self.cmd['deenergize']
        input = self.proc(operation[0])
        self.write.assert_called_with(input)
        self.assertEqual(False, self.tic.enabled)

    def test_move(self):
        operation = self.cmd['sTargetPosition']
        self.tic.enabled = True
        steps = 1000
        self.tic.moveAbsSteps(steps)
        split_input = split32BitSer(steps)
        input = self.proc(operation[0], split_input)
        self.write.assert_called_with(input)

    def test_is_homed(self):
        operation = self.cmd['gVariable']
        variable = self.var['misc_flags1']
        not_home = [1, 1, 1, 1, 1, 1, 1, 1]
        self.read.return_value = not_home
        check_home = self.tic.isHomed()
        input = self.proc(operation[0], [variable[0]])
        self.write.assert_called_with(input)
        self.read.assert_called_with(variable[1])
        self.assertEqual(False, check_home)
        is_home = [1, 0, 1, 1, 1, 1, 1, 1]
        self.read.return_value = is_home
        check_home = self.tic.isHomed()
        self.assertEqual(True, check_home)


def split32BitI2c(input):
    input = int(input)
    output = [input >> 0 & 0xFF,
              input >> 8 & 0xFF,
              input >> 16 & 0xFF,
              input >> 24 & 0xFF]
    return output


def split32BitSer(input):
    input = int(input)
    output = [((input >> 7) & 1)
              | ((input >> 14) & 2)
              | ((input >> 21) & 4)
              | ((input >> 28) & 8),
              input >> 0 & 0x7F,
              input >> 8 & 0x7F,
              input >> 16 & 0x7F,
              input >> 24 & 0x7F]
    return output


if __name__ == '__main__':
    unittest.main()

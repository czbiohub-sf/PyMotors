"""Pololu Tic stepper driver unit tests."""
import unittest
from unittest.mock import patch
import warnings
import pymotors
import tests.fake_smbus2 as fake_smbus2
# pylint: disable=protected-access
# pylint: disable=missing-docstring


class TicI2cUtilities(unittest.TestCase):

    @patch.object(pymotors.tic_stepper.TicI2C, '__init__', return_value=None)
    def setUp(self, mockInit):
        self.stepper = pymotors.tic_stepper.TicI2C(3, 14)
        self.stepper.bus = fake_smbus2.SMBus(3)
        self.stepper.address = 14

    def test_fake_quick_send(self):
        output = self.stepper.send([0x99, 'quick'])
        self.assertEqual([], output)

    def test_fake_7bit_send(self):
        payload = 124
        output = self.stepper.send([0xAA, 7], payload)
        self.assertEqual([], output)

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
        self.assertEqual([], output)

    @patch('pymotors.tic_stepper.i2c_msg', new=fake_smbus2.i2c_msg)
    def test_fake_read(self):
        self.stepper.send([0x00, 'quick'])  # purge native i2c_msg
        self.stepper.bus.fake_register_output = [self.stepper.address, 8]
        read_bits = 8
        payload = [0x33, read_bits]
        output = self.stepper.send([0xCC, 'read'], payload)
        self.assertEqual(self.stepper.bus.fake_register_output, output)

    @patch('pymotors.tic_stepper.i2c_msg')
    def test_fake_32_processing(self, mock_i2c):
        mock_i2c.write = fake_smbus2.i2c_msg.write
        payload = 0x7FFFFFFF
        offset = 0xBB
        address = self.stepper.address
        self.stepper.send([offset, 32], payload)
        data_in = self.stepper.bus.fakeInput()
        self.assertEqual([address, [offset, 0xFF, 0xFF, 0xFF, 0x7F]], data_in)


class TicSerialUtilities(unittest.TestCase):
    @patch('pymotors.tic_stepper.serial')
    def setUp(self, MockSerial):
        port_name = '/dev/ttyacm0'
        baud_rate = 9600
        device_number = 14
        self.stepper = pymotors.tic_stepper.TicSerial(port_name, baud_rate, device_number)

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
        operation = pymotors.tic_stepper.TicStepper._command_dict['energize']
        self.stepper.send(operation)
        expected = self.stepper._makeSerialInput(operation[0])
        self.stepper.port.write.assert_called_with(expected)

    def test_7bit_send(self):
        operation = pymotors.tic_stepper.TicStepper._command_dict['goHome']
        data = 123
        self.stepper.send(operation, data)
        expected = self.stepper._makeSerialInput(operation[0], [data])
        self.stepper.port.write.assert_called_with(expected)

    def test_32bit_send(self):
        operation = pymotors.tic_stepper.TicStepper._command_dict['sMaxSpeed']
        data = 123456
        self.stepper.send(operation, data)
        data_formatting = split32BitSer(data)
        expected = self.stepper._makeSerialInput(operation[0], data_formatting)
        self.stepper.port.write.assert_called_with(expected)

    def test_data_larger_than_7_bit(self):
        operation = pymotors.tic_stepper.TicStepper._command_dict['goHome']
        data = 1234
        try:
            warned = 0
            self.stepper.send(operation, data)
        except ValueError:
            warned = 1
        self.assertEqual(True, warned)

    def test_read(self):
        operation = pymotors.tic_stepper.TicStepper._command_dict['gVariable']
        variable = pymotors.tic_stepper.TicStepper._variable_dict['max_speed']
        self.stepper.port.read.return_value = [1] * variable[1]
        self.stepper.send(operation, variable)
        expected_write = self.stepper._makeSerialInput(operation[0], variable)
        self.stepper.port.write.assert_called_with(expected_write)
        self.stepper.port.read.assert_called_with(variable[1])


class TicStepperI2c(unittest.TestCase):
    @patch('pymotors.tic_stepper.i2c_msg', new=fake_smbus2.i2c_msg)
    @patch('pymotors.tic_stepper.SMBus', new=fake_smbus2.SMBus)
    def setUp(self):
        self.tic = pymotors.tic_stepper.TicStepper('I2C', 3, 14)
        self.cmd = self.tic._command_dict
        self.var = self.tic._variable_dict
        warnings.filterwarnings('error')

    @patch('pymotors.tic_stepper.i2c_msg', new=fake_smbus2.i2c_msg)
    def test_set_microstep(self):
        self.tic.microsteps = 1/8
        data_in = self.tic.com.bus.fakeInput()
        self.assertEqual([self.cmd['sStepMode'][0], 3], data_in[1])
        micros = self.tic.microsteps
        self.assertEqual(1/8, micros)
        self.tic.microsteps = 1/4
        data_in = self.tic.com.bus.fakeInput()
        self.assertEqual([self.cmd['sStepMode'][0], 2], data_in[1])
        self.tic.microsteps = 1/2
        data_in = self.tic.com.bus.fakeInput()
        self.assertEqual([self.cmd['sStepMode'][0], 1], data_in[1])
        self.tic.microsteps = 1
        data_in = self.tic.com.bus.fakeInput()
        self.assertEqual([self.cmd['sStepMode'][0], 0], data_in[1])
        try:
            warned = False
            self.tic.microsteps = 1/6
            data_in = self.tic.com.bus.fakeInput()
        except UserWarning:
            warned = True
        self.assertEqual(True, warned)

    @patch('pymotors.tic_stepper.i2c_msg', new=fake_smbus2.i2c_msg)
    def test_rpm_call(self):
        rpm = 0.1
        self.tic.rpm = rpm
        data_in = self.tic.com.bus.fakeInput()
        steps_per_sec = rpm * self.tic.steps_per_rev / 60
        split_input = split32BitI2c(steps_per_sec * 10000)
        self.assertEqual([self.cmd['sMaxSpeed'][0]] + split_input[:], data_in[1])

    @patch('pymotors.tic_stepper.i2c_msg', new=fake_smbus2.i2c_msg)
    def test_enable(self):
        self.tic.enable = True
        data_in = self.tic.com.bus.fakeInput()
        self.assertEqual(self.cmd['exitSafeStart'][0], data_in[1][0])
        self.assertEqual(True, self.tic.enable)
        self.tic.enable = False
        data_in = self.tic.com.bus.fakeInput()
        self.assertEqual(self.cmd['deenergize'][0], data_in[1][0])
        self.assertEqual(False, self.tic.enable)

    @patch('pymotors.tic_stepper.i2c_msg', new=fake_smbus2.i2c_msg)
    def test_move(self):
        self.tic.enable = True
        self.tic.moveAbsSteps(1000)
        data_in = self.tic.com.bus.fakeInput()
        split_input = split32BitI2c(1000)
        self.assertEqual([self.cmd['sTargetPosition'][0]] + split_input, data_in[1])

    @patch('pymotors.tic_stepper.i2c_msg', new=fake_smbus2.i2c_msg)
    def test_velocity_control(self):
        self.tic.enable = True
        self.tic.velocityControl(2000000)
        data_in = self.tic.com.bus.fakeInput()
        split_input = split32BitI2c(2000000)
        self.assertEqual([self.cmd['sTargetVelocity'][0]] + split_input, data_in[1])

    @patch('pymotors.tic_stepper.i2c_msg', new=fake_smbus2.i2c_msg)
    def test_set_current_limit(self):
        self.tic.setCurrentLimit(13)
        data_in = self.tic.com.bus.fakeInput()
        self.assertEqual([self.cmd['sCurrentLimit'][0]] + [13], data_in[1])


    @patch('pymotors.tic_stepper.i2c_msg', new=fake_smbus2.i2c_msg)
    def test_is_homed(self):
        not_home = 3
        self.tic.com.bus.fake_register_output = not_home
        check_home = self.tic.isHomed()
        data_in = self.tic.com.bus.fakeInput()
        self.assertEqual(self.var['misc_flags1'][0], data_in[1])
        self.assertEqual(False, check_home)
        is_home = 1
        self.tic.com.bus.fake_register_output = is_home
        check_home = self.tic.isHomed()
        self.assertEqual(True, check_home)


class TicStepperSer(unittest.TestCase):
    @patch('pymotors.tic_stepper.serial')
    def setUp(self, MockSerial):
        port_name = '/dev/ttyacm0'
        baud_rate = 9600
        port_params = [port_name, baud_rate]
        address = 14
        self.tic = pymotors.tic_stepper.TicStepper('ser', port_params, address)
        self.write = self.tic.com.port.write
        self.read = self.tic.com.port.read
        self.cmd = self.tic._command_dict
        self.var = self.tic._variable_dict
        self.proc = self.tic.com._makeSerialInput
        warnings.filterwarnings('error')

    def tearDown(self):
        def fake_isMoving():
            return False
        self.tic.isMoving = fake_isMoving

    def test_set_microstep(self):
        operation = self.cmd['sStepMode']
        self.tic.microsteps = 1/8
        data_in = self.proc(operation[0], [3])
        self.write.assert_called_with(data_in)
        micros = self.tic.microsteps
        self.assertEqual(1/8, micros)
        self.tic.microsteps = 1/4
        data_in = self.proc(operation[0], [2])
        self.write.assert_called_with(data_in)
        self.tic.microsteps = 1/2
        data_in = self.proc(operation[0], [1])
        self.write.assert_called_with(data_in)
        self.tic.microsteps = 1
        data_in = self.proc(operation[0], [0])
        self.write.assert_called_with(data_in)
        try:
            warned = False
            self.tic.microsteps = 1/6
        except UserWarning:
            warned = True
        self.assertEqual(True, warned)

    def test_rpm_value_retained(self):
        val = 0.01
        self.tic.rpm = val
        self.assertEqual(val, self.tic.rpm)

    def test_rpm_call(self):
        operation = self.cmd['sMaxSpeed']
        rpm = 2
        self.tic.rpm = rpm
        steps_per_sec = rpm * self.tic.steps_per_rev / 60
        split_input = split32BitSer(steps_per_sec * 10000)
        data_in = self.proc(operation[0], split_input)
        self.write.assert_called_with(data_in)

    def test_enable(self):
        operation = self.cmd['exitSafeStart']
        self.tic.enable = True
        data_in = self.proc(operation[0])
        self.write.assert_called_with(data_in)
        self.assertEqual(True, self.tic.enable)
        self.tic.enable = False
        operation = self.cmd['deenergize']
        data_in = self.proc(operation[0])
        self.write.assert_called_with(data_in)
        self.assertEqual(False, self.tic.enable)

    def test_move(self):
        operation = self.cmd['sTargetPosition']
        self.tic.enable = True
        steps = 1000
        self.tic.moveAbsSteps(steps)
        split_input = split32BitSer(steps)
        data_in = self.proc(operation[0], split_input)
        self.write.assert_called_with(data_in)

    def test_is_homed(self):
        operation = self.cmd['gVariable']
        variable = self.var['misc_flags1']
        not_home = [3]
        self.read.return_value = not_home
        check_home = self.tic.isHomed()
        data_in = self.proc(operation[0], variable)
        self.write.assert_called_with(data_in)
        self.read.assert_called_with(variable[1])
        self.assertEqual(False, check_home)
        is_home = [1]
        self.read.return_value = is_home
        check_home = self.tic.isHomed()
        self.assertEqual(True, check_home)

    def test_set_accel(self):
        ac_val = 10001
        self.tic._setAccel(ac_val)
        operation = self.cmd['sMaxAccel']
        split_input = split32BitSer(ac_val)
        data_in = self.proc(operation[0], split_input)
        self.write.assert_called_with(data_in)

    def test_set_decel(self):
        dc_val = 1000001
        self.tic._setDecel(dc_val)
        operation = self.cmd['sMaxDecel']
        split_input = split32BitSer(dc_val)
        data_in = self.proc(operation[0], split_input)
        self.write.assert_called_with(data_in)

    def test_set_curr_position(self):
        operation = self.cmd['haltAndSetPosition']
        target = 200
        data = split32BitSer(target)
        self.tic._target_steps = 100
        self.tic.setCurrentPositionAs(target)
        data_in = self.proc(operation[0], data)
        self.assertEqual(200, self.tic._target_steps)
        self.write.assert_called_with(data_in)

    def test_is_moving(self):
        operation = self.cmd['gVariable']
        variable = self.var['curr_velocity']
        data_in = self.proc(operation[0], variable)
        self.read.return_value = [0, 0, 0, 0]
        self.tic.isMoving()
        self.write.assert_called_with(data_in)
        self.read.assert_called_with(variable[1])


def split32BitI2c(data_in):
    data_in = int(data_in)
    output = [data_in >> 0 & 0xFF,
              data_in >> 8 & 0xFF,
              data_in >> 16 & 0xFF,
              data_in >> 24 & 0xFF]
    return output


def split32BitSer(data_in):
    data_in = int(data_in)
    output = [((data_in >> 7) & 1)
              | ((data_in >> 14) & 2)
              | ((data_in >> 21) & 4)
              | ((data_in >> 28) & 8),
              data_in >> 0 & 0x7F,
              data_in >> 8 & 0x7F,
              data_in >> 16 & 0x7F,
              data_in >> 24 & 0x7F]
    return output


if __name__ == '__main__':
    unittest.main()

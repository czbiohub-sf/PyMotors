import unittest
from unittest.mock import patch
import warnings
import src
import tests.fake_smbus2 as fake_smbus2


class TicI2c_Utilities(unittest.TestCase):

    @patch.object(src.tic_stepper.TicI2C, '__init__', return_value=None)
    def setUp(self, mockInit):
        self.stepper = src.tic_stepper.TicI2C(3, 14)
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

    @patch('src.tic_stepper.i2c_msg', new=fake_smbus2.i2c_msg)
    def test_fake_read(self):
        self.stepper.send([0x00, 'quick'])  # purge native i2c_msg
        self.stepper.bus.fake_register_output = [1, 2, 3, 4, 5, 6, 7, 8]
        read_bits = 8
        payload = [0x33, read_bits]
        output = self.stepper.send([0xCC, 'read'], payload)
        self.assertEqual(self.stepper.bus.fake_register_output, output)

    @patch('src.tic_stepper.i2c_msg')
    def test_fake_32_processing(self, mockI2c):
        mockI2c.write = fake_smbus2.i2c_msg.write
        payload = 0x7FFFFFFF
        offset = 0xBB
        address = self.stepper.address
        self.stepper.send([offset, 32], payload)
        input = self.stepper.bus.fakeInput()
        self.assertEqual([address, [offset, 0xFF, 0xFF, 0xFF, 0x7F]], input)


class TicStepper_Utilities(unittest.TestCase):
    @patch('src.tic_stepper.i2c_msg', new=fake_smbus2.i2c_msg)
    @patch('src.tic_stepper.SMBus', new=fake_smbus2.SMBus)
    def setUp(self):
        warnings.filterwarnings('ignore')
        self.tic = src.tic_stepper.TicStepper('I2C', 3, 14)
        warnings.filterwarnings('error')

    @patch('src.tic_stepper.i2c_msg', new=fake_smbus2.i2c_msg)
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

    @patch('src.tic_stepper.i2c_msg', new=fake_smbus2.i2c_msg)
    def test_steps_per_second(self):
        self.tic.steps_per_second = .01
        input = self.tic.com.bus.fakeInput()
        split_input = split32BitI2c(self.tic.steps_per_second * 10000)
        self.assertEqual([self.tic.command_dict['sMaxSpeed'][0]] + split_input[:], input[1])

    @patch('src.tic_stepper.i2c_msg', new=fake_smbus2.i2c_msg)
    def test_enabled(self):
        self.tic.enabled = True
        input = self.tic.com.bus.fakeInput()
        self.assertEqual(self.tic.command_dict['exitSafeStart'][0], input[1])
        self.assertEqual(True, self.tic.enabled)
        self.tic.enabled = False
        input = self.tic.com.bus.fakeInput()
        self.assertEqual(self.tic.command_dict['deenergize'][0], input[1])
        self.assertEqual(False, self.tic.enabled)

    @patch('src.tic_stepper.i2c_msg', new=fake_smbus2.i2c_msg)
    def test_move(self):
        self.tic.enabled = True
        self.tic.moveAbsSteps(1000)
        input = self.tic.com.bus.fakeInput()
        split_input = split32BitI2c(1000)
        self.assertEqual([self.tic.command_dict['sTargetPosition'][0]] + split_input, input[1])

    @patch('src.tic_stepper.i2c_msg', new=fake_smbus2.i2c_msg)
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


def split32BitI2c(input):
    input = int(input)
    output = [input >> 0 & 0xFF,
              input >> 8 & 0xFF,
              input >> 16 & 0xFF,
              input >> 24 & 0xFF]
    return output


if __name__ == '__main__':
    unittest.main()

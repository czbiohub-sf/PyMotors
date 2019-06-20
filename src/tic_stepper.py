import warnings
from src.stepper_base import StepperBase
try:  # Import I2C module
    from smbus2 import SMBus, i2c_msg
except ImportError:
    print('Unable to import smbus2 for Tic I2C communication.')
try:  # Import serial module
    import serial
except ImportError:
    print('Unable to import serial for Tic serial communication.')


class TicStepper(StepperBase):

    com_protocol = {'SERIAL': 0, 'I2C': 1}

    def __init__(self, type: str,
                 port_params,
                 address=None,
                 input_microsteps=1,
                 input_units_per_step=1,
                 input_units_per_second=10):

        warnings.warn("Tic settings must be set with USB prior to use.")

        if self._communicationProtocol(type) == self.com_protocol['SERIAL']:
            port_name = port_params[0]  # '/dev/ttyacm0'
            baud_rate = port_params[1]  # 9600
            port = serial.Serial(port_name, baud_rate,
                                 timeout=0.1, write_timeout=0.1)
            self.com = TicSerial(port, address)

        elif self._communicationProtocol(type) == self.com_protocol['I2C']:
            self.com = TicI2C(port_params, address)

        self._makeCommandDict()
        self._makeVariableDict()
        super(TicStepper, self).__init__(input_microsteps,
                                         input_units_per_step,
                                         input_units_per_second)

    def home(self, dir: str):
        available = self._checkLimitSwitch(dir)
        if available:
            command_to_send = self.command_dict['goHome']
            data = dir
            self.com.send(command_to_send, data)
        else:
            warnings.warn('Limit switch not available in direction: ' + dir)

    def isHomed(self):
        command_to_send = self.command_dict['gVariable']
        data = self.variable_dict['misc_flags1']
        b = self.com.send(command_to_send, data)
        return b[1] == 0

    @property
    def enabled(self):
        """bool : Enable or disable the motor."""
        return self._enabled

    @enabled.setter
    def enabled(self, state):
        """
        Enable or disable the motor.

        Parameters
        ----------
        state : bool
        The desired motor state.

        Warnings
        --------
        UserWarning
        If state is not a binary value.

        Notes
        -----
        Can be overloaded to apply implementation specific hardware enabling.

        """
        if state == self._enable_states['DISABLED']:
            self._enabled = self._enable_states['DISABLED']
            self.com.send(self.command_dict['enterSafeStart'])
            self.com.send(self.command_dict['deenergize'])
        elif state == self._enable_states['ENABLED']:
            self._enabled = self._enable_states['ENABLED']
            self.com.send(self.command_dict['energize'])
            self.com.send(self.command_dict['exitSafeStart'])
        else:
            warnings.warn('Expected `False` (disabled) or `True` (enabled)')

    def _position_in_steps(self):
        command_to_send = self.command_dict['gVariable']
        data = self.variable_dict['curr_position']
        b = self.com.send(command_to_send, data)
        location = b[0] + (b[1] << 8) + (b[2] << 16) + (b[3] << 24)
        if location >= (1 << 31):
            location -= (1 << 32)
            return location

    def _moveToTarget(self):
        command_to_send = self.command_dict['sTargetPosition']
        data = self._target_steps
        self.com.send(command_to_send, data)

    def _checkLimitSwitch(self, direction: str):
        command_to_send = self.command_dic['gSetting']
        if direction == 'fwd':
            data = self.setting_dict['limit_switch_fwd']
        elif direction == 'rev':
            data = self.setting_dict['limit_switch_rev']
        else:
            warnings.warn('Direction should be `fwd` or `rev`')
            return 0
        limit_switch = self.com.send(command_to_send, data)
        if limit_switch == 0:
            return 0
        return 1

    def _setMicrostep(self, microstep: int):
        self._microsteps = microstep
        command_to_send = self.command_dict['sStepMode']
        data = (microstep == 0b10) + (microstep == 0b100)*2 + (microstep == 0b1000)*3
        self.com.send(command_to_send, data)

    def _setSpeed(self, speed):
        command_to_send = self.command_dict['sMaxSpeed']
        data = speed * 10000
        self.com.send(command_to_send, data)

    def _communicationProtocol(self, type: str):
        if type in ('serial', 'ser', 'Serial'):
            return self.com_protocol['SERIAL']
        elif type in ('i2c', 'I2C'):
            return self.com_protocol['I2C']
        else:
            raise ValueError('Expected protocol type `serial` or `i2c`.')

    def _makeCommandDict(self):  # Entries selected for T500
        self.command_dict = \
            {  # 'commandKey': [command_address, operation] # Data
                'sTargetPosition': [0xE0, 32],  # microsteps
                'sTargetVelocity': [0xE3, 32],  # microsteps / 10,000s
                'haltAndSetPosition': [0xEC, 32],  # microsteps
                'haltAndHoldPosition': [0x89, 'quick'],  # NONE
                'goHome': [0x97, 7],  # 0: rev, 1: fwd
                'rstCommandTimeout': [0x8C, 'quick'],  # NONE
                'deenergize': [0x86, 'quick'],  # NONE
                'energize': [0x85, 'quick'],  # NONE
                'exitSafeStart': [0x83, 'quick'],  # NONE
                'enterSafeStart': [0x8F, 'quick'],  # NONE
                'rst': [0xB0, 'quick'],  # NONE
                'clrDriverError': [0x8A, 'quick'],  # NONE
                'sMaxSpeed': [0xE6, 32],  # microsteps / 10,000s
                'sStartingSpeed': [0xE5, 32],  # microsteps / 10,000s
                'sMaxAccel': [0xEA, 32],  # microsteps / 100(s^2)
                'sMaxDecel': [0xE9, 32],  # microsteps / 100(s^2)
                'sStepMode': [0x94, 7],  # 0<=n<=3 (microsteps = 2^n)
                'sCurrentLimit': [0x91, 7],  # 0 to 124
                'gVariable': [0xA1, 'read'],  # block read
                'gVarAndClearErrs': [0xA2, 'read'],  # block read
                'gSetting': [0xA8, 'read'],  # block read
            }  # documentation: https://www.pololu.com/docs/0J71/8

    def _makeVariableDict(self):
        self.variable_dict = \
            {  # 'variable_key': [offset_address, bits_to_read]
                'operation_state': [0x00, 8],
                'misc_flags1': [0x01, 8],
                'error_status': [0x02, 16],
                'errors_occured': [0x04, 32],
                'planning_mode': [0x09, 8],
                'target_position': [0x0A, 32],
                'target_velocity': [0x0E, 32],
                'starting_speed': [0x12, 32],
                'max_speed': [0x16, 32],
                'max_accel': [0x1A, 32],
                'max_decel': [0x1E, 32],
                'curr_position': [0x22, 32],
                'curr_velocity': [0x26, 32],
                'acting_tar_pos': [0x2A, 32],
                'time_since_last_step': [0x2E, 32],  # 1/3us
                'device_rst': [0x32, 8],
                'vin_voltage': [0x33, 16],
                'uptime': [0x35, 32],
                'encoder_pos': [0x39, 32],
                'rc_pulse_width': [0x3D, 16],
                'analog_reading_SCL': [0x3F, 16],
                'analog_reading_SDA': [0x41, 16],
                'analog_reading_TX': [0x43, 16],
                'analog_reading_RX': [0x45, 16],
                'digital_readings': [0x47, 8],
                'pin_states': [0x48, 8],
                'step_mode': [0x49, 8],
                'current_limit': [0x4A, 8],
                'input_state': [0x4C, 8],
                'last_driver_error': [0x55, 8],
            }  # documentation: https://www.pololu.com/docs/0J71/7

    def _makeSettingDict(self):
        self.setting_dict = \
            {
                'limit_switch_fwd': [0x5F, 8],
                'limit_switch_rev': [0x60, 8],
            }


class TicSerial(object):
    def __init__(self, port, device_number=None):
        self.port = port
        self.device_number = device_number

    def _makeSerialInput(self, offset, data=None):
        if self.device_number is None:
            header = [offset]  # Compact protocol
        else:
            header = [0xAA, self.device_number, offset & 0x7F]
            bytes(header + data)

    def send(self, operation: list, data=None):
        offset = operation[0]
        protocol = operation[1]
        if protocol[1] == 'quick':  # Quick write
            command = self._makeSerialInput(offset)
            read = False
        elif protocol[1] == 'read':  # Block read
            command = self._makeSerialInput(offset, data)
            read = True
        elif protocol[1] == 7:  # 7-bit write
            data = int(data)
            command = self._makeSerialInput(offset, list(data))
            read = False
        elif protocol[1] == 32:  # 32-bit write
            data = int(data)
            command = self._makeSerialInput(offset,
                                            [((data >> 7) & 1)
                                             | ((data >> 14) & 2)
                                             | ((data >> 21) & 4)
                                             | ((data >> 28) & 8),
                                             data >> 0 & 0x7F,
                                             data >> 8 & 0x7F,
                                             data >> 16 & 0x7F,
                                             data >> 24 & 0x7F])
            read = False

        if read is False:
            self.port.write(command)
        else:
            self.port.write(command)
            result = self.port.read(data[1])
            if len(result) != data[1]:
                raise RuntimeError("Expected to read {} bytes, got {}."
                                   .format(data[1], len(result)))
            return bytearray(result)


class TicI2C(object):
    def __init__(self, bus, address):
        self.bus = SMBus(bus)
        self.address = address

    def send(self, operation: list, data=None):
        offset = operation[0]
        protocol = operation[1]
        if protocol == 'quick':  # Quick write
            command = offset
            read = None
        elif protocol == 'read':  # Block read
            command = [offset, data[0]]
            read = i2c_msg.read(self.address, data[1])
        elif protocol == 7:  # 7-bit write
            command = [offset, int(data)]
            read = None
        elif protocol == 32:  # 32-bit write
            data = int(data)
            command = [offset,
                       data >> 0 & 0xFF,
                       data >> 8 & 0xFF,
                       data >> 16 & 0xFF,
                       data >> 24 & 0xFF]
            read = None
        else:
            warnings.warn('Protocol `{}` not recognized.'.format(protocol))

        write = i2c_msg.write(self.address, command)
        if read is None:
            self.bus.i2c_rdwr(write)
        else:
            self.bus.i2c_rdwr(write, read)
            return list(read)

# Process 32-bit read
#    # Gets the "Current position" variable from the Tic.
#    def get_current_position(self):
#        b = self.get_variables(0x22, 4)
#        position = b[0] + (b[1] << 8) + (b[2] << 16) + (b[3] << 24)
#        if position >= (1 << 31):
#            position -= (1 << 32)
#            return position

# Custom methods written to generalize the methods provided by Adafruit
#    def writeQuick(self, offset):
#        command = [offset]
#        write = i2c_msg.write(self.address, command)
#        self.bus.i2c_rdwr(write)
#
#    def write7Bit(self, offset, data):
#        print()
#
#    def write32Bit(self, offset, data):
#        command = [offset,
#                   data >> 0 & 0xFF,
#                   data >> 8 & 0xFF,
#                   data >> 16 & 0xFF,
#                   data >> 24 & 0xFF]
#        write = i2c_msg.write(self.address, command)
#        self.bus.i2c_rdwr(write)
#
#    def readBlock(self, offset, length):
#        write = i2c_msg.write(self.address, [0xA1, offset])
#        read = i2c_msg.read(self.address, length)
#        self.bus.i2c_rdwr(write, read)
#        return list(read)
#

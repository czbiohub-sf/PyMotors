"""Utilities for interfacing with a Pololu Tic T500 stepper driver.

Communication protocols that are currently supported include I2C (TicI2C) and
TTL serial (TicSerial). To support other Tic stepper drivers, add relevant
commands and variables that may be absent. Before using the following code
with your Tic stepper driver, preconfigure the board with USB. Settings cannot
be changed via I2C or serial - only variables can be.

Recommended setups:
Raspberry Pi with I2C or serial implmentation and bidirectional level shifters.
PC with serial implementation and a USB-to-UART cable (5V TTL).

"""
import warnings
from .stepper_base import StepperBase
try:  # Import I2C module
    from smbus2 import SMBus, i2c_msg
except ImportError:
    print('Unable to import smbus2 for Tic I2C communication.')
try:  # Import serial module
    import serial
except ImportError:
    print('Unable to import pyserial for Tic serial communication.')

# pylint: disable=invalid-name

# ---------------------------------------CONSTANTS-----------------------------------------------
_MAX_RESP_BITS = 8
_OBJECT_TYPE = "TicStage"

# Uses bit flags
_error_status_dict = {
        0: "Intentionally de-energized",
        1: "Motor driver error",
        2: "Low VIN",
        3: "Kill switch active",
        4: "Required input invalid",
        5: "Serial error",
        6: "Command timeout",
        7: "Safe start violation",
        8: "ERR line high"}

# Uses bit flags
_misc_bit_dict = {
        0: "Energized",
        1: "Position uncertain",
        2: "Forward limit active",
        3: "Reverse limit active",
        4: "Homing active"}

# Uses a map from integer to status string
_op_state_dict = {
        0: "Reset",
        2: "De-engergized",
        4: "Soft error",
        6: "Waiting for ERR line",
        8: "Starting up",
        10: "Normal"}


class TicStepper(StepperBase):
    """Base class for Pololu Tic stepper driver.

    Parameters
    ----------
    com_type : str
        Communication protocol `I2C` or `SERIAL`.
    port_params : list or int
        (Serial) -> [port: str, baud: int] || (I2C) -> port: int.
    address : int
        Device address on bus.
    input_dist_per_rev : float
        Conversion factor of user defined distance units per revolution.
    input_steps_per_rev : int
        Number of steps per revolution.
    input_rpm : float
        Initial max speed in revolutions per minute.

    Attributes
    ----------
    microsteps : float
        Ratio of full steps to microsteps.
    dist_per_rev : float
        Number of user defined units per revolution.
    dist_per_min : float
        Speed in user defined distance units per minute.
    rpm : float
        Max speed of stepper motor in revolutions per minute.
    enable : bool
        Enable or disable stepper motion.

    """

    def __init__(self, com_type: str,
                 port_params,
                 address=None,
                 input_dist_per_rev=1,
                 input_steps_per_rev=200,
                 input_rpm=1):

        if self._comProtocol(com_type) == self._com_protocol['SERIAL']:
            port_name = port_params[0]  # ex: '/dev/ttyUSB0'
            baud_rate = port_params[1]  # ex: 9600
            self.com = TicSerial(port_name, baud_rate, address)

        elif self._comProtocol(com_type) == self._com_protocol['I2C']:
            self.com = TicI2C(port_params, address)
        self.com.send(self._command_dict['rst'])
        super(TicStepper, self).__init__(input_dist_per_rev,
                                         input_steps_per_rev,
                                         input_rpm)

    def __del__(self):
        self.enable = False

    @property
    def accel_decel(self) -> list:
        """Acceleration and deceleration values."""
        curr_accel = self.com.send(self._command_dict['gVariable'],
                                   self._variable_dict['max_accel'])
        curr_decel = self.com.send(self._command_dict['gVariable'],
                                   self._variable_dict['max_decel'])
        int_accel = self.bytesToInt(curr_accel)
        int_decel = self.bytesToInt(curr_decel)
        return [int_accel, int_decel]

    @accel_decel.setter
    def accel_decel(self, accel_decel_vals: list):
        if accel_decel_vals[0] > 0 and accel_decel_vals[1] > 0:
            accel = accel_decel_vals[0]
            decel = accel_decel_vals[1]
            self._setAccel(accel)
            self._setDecel(decel)
        else:
            warnings.warn("Acceleration and/or deceleration must be > 0")

    @staticmethod
    def bytesToInt(b: list) -> int:
        """Convert 16- or 32-bit output to int."""
        val = b[0] + (b[1] << 8)
        try:
            val = val + (b[2] << 16) + (b[3] << 24)
        finally:
            return val

    def checkLimitSwitch(self, direction: str) -> bool:
        """Confirm that limit switch exists in homing direction `direction`."""
        command_to_send = self._command_dict['gSetting']
        if direction == 'fwd':
            data = self._setting_dict['limit_switch_fwd']
        elif direction == 'rev':
            data = self._setting_dict['limit_switch_rev']
        else:
            warnings.warn('Direction should be `fwd` or `rev`')
            return False
        limit_switch = self.com.send(command_to_send, data)
        if limit_switch == 0:
            return False
        return True

    @property
    def enable(self):
        """
        Check the enable state of the motor.

        Returns
        -------
        _enable : bool
            True if the motor is enable, False if the motor is disabled.
        """
        return self._enable

    @enable.setter
    def enable(self, state):
        """
        Enable or disable the motor.

        Parameters
        ----------
        state : bool
            The desired motor state.

        """
        if state == self._enable_states['DISABLED']:
            self._enable = self._enable_states['DISABLED']
            self.com.send(self._command_dict['enterSafeStart'])
            self.com.send(self._command_dict['deenergize'])
        elif state == self._enable_states['ENABLED']:
            self._enable = self._enable_states['ENABLED']
            self.com.send(self._command_dict['energize'])
            self.com.send(self._command_dict['exitSafeStart'])
        else:
            warnings.warn('Expected `False` (disabled) or `True` (enable)')

    def getCurrentPositionSteps(self):
        return self.getPosition("steps")

    def halt(self):
        """Stop the motor abruptly at the current postition."""
        command_to_send = self._command_dict['haltAndHoldPosition']
        self.com.send(command_to_send)

    def home(self, direc: str):
        """
        Home the motor in the specified direction.

        Parameters
        ----------
        direc : str
        The direction to home. Supported values: `fwd` or `rev`.

        Notes
        -----
        Limit switches must be preconfigured via USB before use.

        """
        limit_available = self.checkLimitSwitch(direc)
        if limit_available:
            command_to_send = self._command_dict['goHome']
            if direc == 'fwd':
                data = 1
            else:
                data = 0
            self.com.send(command_to_send, data)
        else:
            warnings.warn('Limit switch not available in direction: ' + direc)

    def isHomed(self) -> bool:
        """Check the 'position uncertain' bit on the Tic driver.

        The flag 'position uncertain' will be 1 if the motor is de-energized
        or contacts a limit switch. Home to clear the flag.

        Returns
        -------
        position_known : bool
            True if 'position uncertain' flag is not set.
        """
        command_to_send = self._command_dict['gVariable']
        data = self._variable_dict['misc_flags1']
        b = self.com.send(command_to_send, data)
        position_known = (b[0] & 2) == 0
        return position_known

    def isMoving(self) -> bool:
        """Check the 'current velocity' value of the Tic driver."""
        command_to_send = self._command_dict['gVariable']
        data = self._variable_dict['curr_velocity']
        b = self.com.send(command_to_send, data)
        velocity = self.bytesToInt(b)
        return velocity != 0

    def setCurrentLimit(self, milliamp_code: int):
        """Review https://www.pololu.com/docs/0J71/6#setting-current-limit ."""
        command_to_send = self._command_dict['sCurrentLimit']
        data = milliamp_code
        self.com.send(command_to_send, data)

    def setCurrentPositionAs(self, positionSteps: int):
        """Zero the current position."""
        if type(positionSteps) != int:
            warnings.warn('"positionSteps" must be an integer')
            return

        command_to_send = self._command_dict['haltAndSetPosition']
        data = positionSteps
        self.com.send(command_to_send, data)
        self._target_steps = positionSteps

    def velocityControl(self, steps_per_10000s):
        """Set the motor to move at the specified velocity."""

        command_to_send = self._command_dict['sTargetVelocity']
        data = steps_per_10000s
        self.com.send(command_to_send, data)
    
    def _comProtocol(self, com_type: str) -> int:
        """Determine communication protocol from user input."""
        if com_type in ('serial', 'ser', 'Serial'):
            protocol = self._com_protocol['SERIAL']
        elif com_type in ('i2c', 'I2C'):
            protocol = self._com_protocol['I2C']
        else:
            raise ValueError('Expected protocol com_type `serial` or `i2c`.')
        return protocol

    def _moveToTarget(self):
        """Communicate with Tic board to set target position in steps."""

        command_to_send = self._command_dict['sTargetPosition']
        data = self._target_steps
        self.com.send(command_to_send, data)

    def _position_in_steps(self):
        """Process Tic output for location in steps.

        32-bit readings return bytes in reverse order. Elements need to be
        shifted accordingly and the sign of the value needs to be checked.
        """
        command_to_send = self._command_dict['gVariable']
        data = self._variable_dict['curr_position']
        b = self.com.send(command_to_send, data)
        location = self.bytesToInt(b)
        if location >= (1 << 31):
            location -= (1 << 32)
        return location

    def _setAccel(self, val: int):
        """Communicate with the Tic board to set max acceleration.

        Parameters
        ----------
        val : int
            Max acceleration value in microsteps/s^2.

        """
        command_to_send = self._command_dict['sMaxAccel']
        data = val
        self.com.send(command_to_send, data)

    def _setDecel(self, val: int):
        """Communicate with the Tic board to set max Deceleration.

        Parameters
        ----------
        val : int
            Max deceleration value in microsteps/s^2.

        """
        command_to_send = self._command_dict['sMaxDecel']
        data = val
        self.com.send(command_to_send, data)

    def _setMicrostep(self, microstep: int):
        """Communicate with the Tic board to set microsteps 
        (this initialization is temporary and resets back to setting configuration
        on reset/reinitialize command or microcontroller reset).
        
        Parameters
        ----------
        microsteps : int
            Number of microsteps per full-step, allowable values
            are 1, 2, 4, 8 for the T500 (https://www.pololu.com/docs/0J71/8#cmd-set-step-mode)
        """

        self._microsteps_per_full_step = microstep
        command_to_send = self._command_dict['sStepMode']
        data = (microstep == 0b10) \
            + (microstep == 0b100) * 2 \
            + (microstep == 0b1000) * 3
        self.com.send(command_to_send, data)

    def _setSpeed(self, speed: float):
        """Communicate with the Tic board to set velocity in steps / 10000s."""
        command_to_send = self._command_dict['sMaxSpeed']
        data = speed * 10000
        print(f"Speed: {speed}")
        self.com.send(command_to_send, data)

    def _getmotor_status(self) -> tuple:
        """Poll the tic flag for position certainty

        Returns
        -------
        A 3-Tuple with the various tic stage status responses.
        If an error occurs, returns False, False, False
        See getAndParsemotor_status() for parsed output.
        """

        try:
            misc_resp = self.com.send(self._command_dict['gVariable'], self._variable_dict['misc_flags1'])
            err_resp = self.com.send(self._command_dict['gVariable'], self._variable_dict['error_status'])
            op_resp = self.com.send(self._command_dict['gVariable'], self._variable_dict['operation_state'])
        except Exception as e:
            print("Error reading motor status")
            print(e)
            return False, False, False

        return misc_resp, err_resp, op_resp

    def getAndParsemotor_status(self)-> dict:
        """Gets all the status reports from the motor and translates them into english for printing/display

        Returns
        -------
        motor_status : dict
            Three item dictionary with OperationStatus, ErrorStatus, and PositionStatus.
        """

        # Poll the motor for statuses
        misc_resp, err_resp, op_resp = self._getmotor_status()

        # Parse the responses
        misc_msg = list()
        op_msg = list()
        err_msg = list()
        for i in range(_MAX_RESP_BITS):
            if misc_resp[0] & 2**i:
                misc_msg.append(_misc_bit_dict[i])
            # op_resp format is not a bit lookup - they are just even integers
            if op_resp[0] == 2*i:
                op_msg.append(_op_state_dict[2*i])
            if err_resp[0] & 2**i:
                err_msg.append(_error_status_dict[i])

        motor_status = {'OperationStatus': op_msg, \
                       'ErrorStatus': err_msg, \
                       'PositionStatus': misc_msg}

        return motor_status

    def print(self):
        """Print status of this object to the command line"""

        motor_status = self.getAndParsemotor_status()
        print('\n------------------')
        print(_OBJECT_TYPE)
        print('------------------\n')

        print('TicStepper attributes:')
        print('------------------\n')

        for key in motor_status.keys():
            print(key)
            for value in motor_status[key]:
                print('---------'+ value)
        print('------------------\n')

    _com_protocol = {'SERIAL': 0, 'I2C': 1}

    _command_dict = \
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

    _variable_dict = \
        {  # 'variable_key': [offset_address, bytes_to_read]
            'operation_state': [0x00, 1],
            'misc_flags1': [0x01, 1],
            'error_status': [0x02, 2],
            'errors_occured': [0x04, 4],
            'planning_mode': [0x09, 1],
            'target_position': [0x0A, 4],
            'target_velocity': [0x0E, 4],
            'starting_speed': [0x12, 4],
            'max_speed': [0x16, 4],
            'max_decel': [0x1A, 4],
            'max_accel': [0x1E, 4],
            'curr_position': [0x22, 4],
            'curr_velocity': [0x26, 4],
            'acting_tar_pos': [0x2A, 4],
            'time_since_last_step': [0x2E, 4],  # 1/3us
            'device_rst': [0x32, 1],
            'vin_voltage': [0x33, 2],
            'uptime': [0x35, 4],
            'encoder_pos': [0x39, 4],
            'rc_pulse_width': [0x3D, 2],
            'analog_reading_SCL': [0x3F, 2],
            'analog_reading_SDA': [0x41, 2],
            'analog_reading_TX': [0x43, 2],
            'analog_reading_RX': [0x45, 2],
            'digital_readings': [0x47, 1],
            'pin_states': [0x48, 1],
            'step_mode': [0x49, 1],
            'current_limit': [0x4A, 1],
            'input_state': [0x4C, 1],
            'last_driver_error': [0x55, 1],
        }  # documentation: https://www.pololu.com/docs/0J71/7


    _setting_dict = \
        {
            'limit_switch_fwd': [0x5F, 1],
            'limit_switch_rev': [0x60, 1],
        }


class TicSerial():
    """
    Serial communication protocol for operating a Tic stepper driver.

    Attributes
    ----------
    port : str
        String specifying port address.

    device_number : int
        Int specifying device number on bus.
    """

    def __init__(self, port_name, baud_rate, device_number=None):
        self.port = serial.Serial(port_name, baud_rate,
                                  timeout=0.1, write_timeout=0.1)
        self.device_number = device_number

    def __del__(self):
        self.port.close()

    def _makeSerialInput(self, offset, data=None):
        if self.device_number is None:
            header = [offset]  # Compact protocol
        else:
            header = [0xAA, self.device_number, offset & 0x7F]
        if data is None:
            ret = bytes(header)
        else:
            ret = bytes(header + list(data))
        return ret

    def send(self, operation: list, data: list = None) -> list:
        """
        Interface for communicating with the Tic stepper driver.

        Parameters
        ----------
        operation : list
            Specifies command offset and write/read operation type.

        data : list
            Data to pass to the registers at offset specified in operation.

        Returns
        -------
        result : list
            Data read from Tic registers, broken into a list of bytes.
        """
        offset = operation[0]
        protocol = operation[1]
        if protocol == 'quick':  # Quick write
            command = self._makeSerialInput(offset)
            read = False
        elif protocol == 'read':  # Block read
            command = self._makeSerialInput(offset, data)
            read = True
        elif protocol == 7:  # 7-bit write
            data = [int(data)]
            command = self._makeSerialInput(offset, data)
            read = False
        elif protocol == 32:  # 32-bit write
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
            ret = []
        else:
            self.port.write(command)
            result = self.port.read(data[1])
            if len(result) != data[1]:
                raise RuntimeError("Expected to read {} bytes, got {}."
                                   .format(data[1], len(result)))
            ret = bytearray(result)
        return ret


class TicI2C():
    """
    I2C communication protocol for operating a Tic stepper driver.

    Attributes
    ----------
    bus : SMBus
        SMBus object for managing I2C port.

    address : int
        Int specifying the device address on the bus.
    """

    def __init__(self, bus, address):
        self.bus = SMBus(bus)
        self.address = address

    def __del__(self):
        self.bus.close()

    def send(self, operation: list, data=None) -> list:
        """
        Interface for communicating with the Tic stepper driver.

        Parameters
        ----------
        operation : list
            Specifies command offset and write/read operation type.

        data : list
            Data to pass to the registers at offset specified in operation.

        Returns
        -------
        read : list
            Data read from Tic registers, broken into a list of bytes.
        """
        offset = operation[0]
        protocol = operation[1]
        if protocol == 'quick':  # Quick write
            command = [offset]
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
        self.bus.i2c_rdwr(write)
        ret = []
        if read is not None:
            self.bus.i2c_rdwr(read)
            ret = list(read)
        return ret

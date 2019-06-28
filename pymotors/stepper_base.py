import warnings


class StepperBase():
    """
    Base class for interfacing with stepper motors while being agnostic to
    implementation specifics. Provides movement commands in absolute and
    relative positions described in steps or units per step.

    Attributes
    ----------
    microsteps : int
        Ratio of full steps to microsteps.
    units_per_step : float
        Conversion factor converting steps into user defined units.
    steps_per_second : float
        Stepper speed in steps
    units_per_second : float
        Stepper speed in user defined units.
    enabled : bool
        Software lock on stepper motion.

    Notes
    -----
    If using `units`, set microsteps before units_per_step if using microsteps.
    Set units_per_step before units_per_second.
    """
    _enable_states = {'DISABLED': False, 'ENABLED': True}
    _unit_type = {'UNKNOWN': -1, 'STEPS': 0, 'UNITS': 1}

    def __init__(self, input_microsteps=1, input_units_per_step=1,
                 input_units_per_second=10):
        self.microsteps = input_microsteps
        self.units_per_step = input_units_per_step
        self._steps_per_second = input_units_per_second
        self._enabled = self._enable_states['DISABLED']
        self._target_steps = 0

    @property
    def microsteps(self):
        """
        float: Fraction of a stepper motor full step per pulse.
        """
        return 1 / self._microsteps_per_full_step

    @microsteps.setter
    def microsteps(self, step_ratio: float):
        micros_per_full_step = 1 / step_ratio
        if self._checkMicrostep(micros_per_full_step):
            self._setMicrostep(micros_per_full_step)
        else:
            warnings.warn("Microstep value not available.")

    @property
    def units_per_step(self):
        """float : Conversion factor for steps to units of interest."""
        return self._units_per_step

    @units_per_step.setter
    def units_per_step(self, units: float):
        self._units_per_step = units

    @property
    def steps_per_second(self):
        """float : Speed in steps per second."""
        return self._steps_per_second

    @steps_per_second.setter
    def steps_per_second(self, speed: float):
        if speed > 0:
            self._steps_per_second = speed
            self._setSpeed(speed)
        else:
            warnings.warn("Speed must be greater than 0.")

    @property
    def units_per_second(self):
        """float : Speed in units per second."""
        return self._convStepsToUnits(self._steps_per_second)

    @units_per_second.setter
    def units_per_second(self, speed: float):
        """Set units_per_step before calling units_per_second."""
        if speed > 0:
            self._steps_per_second = self._convUnitsToSteps(speed)
        else:
            warnings.warn("Speed must be greater than 0.")

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
        Can be overridden to apply implementation specific hardware enabling.

        """
        if state == self._enable_states['DISABLED']:
            self._enabled = self._enable_states['DISABLED']
        elif state == self._enable_states['ENABLED']:
            self._enabled = self._enable_states['ENABLED']
        else:
            warnings.warn('Expected `False` (disabled) or `True` (enabled)')

    def moveAbsSteps(self, target_steps: int):
        """Move to target step position."""
        if self._enabled:
            self._target_steps = target_steps
            self._moveToTarget()
        else:
            warnings.warn("Motor is not enabled and cannot move.")

    def moveRelSteps(self, rel_target_steps: int):
        """"Move target steps away from current position."""
        target_steps = round(self._convReltoAbs(rel_target_steps))
        self.moveAbsSteps(target_steps)

    def moveAbsUnits(self, target_units: float):
        """Move to target unit position."""
        target_steps = round(self._convUnitsToSteps(target_units))
        self.moveAbsSteps(target_steps)

    def moveRelUnits(self, rel_target_units: float):
        """Move target units away from current position."""
        rel_target_steps = self._convUnitsToSteps(rel_target_units)
        self.moveRelSteps(rel_target_steps)

    def position(self, type: str):
        """
        Current position.

        Parameters
        ----------
        type : str
            The desired interpretation of the current position.

        Returns
        -------
        position : int
            Position in either absolute units or absolute steps.

        Warnings
        --------
        UserWarning
            If `units` or `steps` were not provided as an argument.
        """
        output_type = self._typeSorter(type)
        if output_type == self._unit_type['STEPS']:
            return self._position_in_steps()
        elif output_type == self._unit_type['UNITS']:
            return self._convStepsToUnits(self._position_in_steps())

    def isMoving(self):
        """Motor has not arrived at commanded position."""
        return self.position('steps') != self._target_steps

    def stop(self):
        """
        Stops movement by setting current position to target position. Also,
        disable the motor to ignore queued movement commands.
        """
        self._target_steps = self.position('steps')
        self.enabled = self._enable_states['DISABLED']

    def _moveToTarget(self):
        """
        Step the motor towards the target position.

        Parameters
        ----------
        target_position : int
            The absolute position to travel to in units of steps.

        Raises
        ------
        NotImplementedError
            If _moveTo has not been overridden with an implementation specific
            function.

        Notes
        -----
        Function should account for _target_steps when implemented.
        Function should account for the current position in absolute steps.
        Function should account for _steps_per_second when implemented.
        """
        raise NotImplementedError('_moveTo is not overridden.')

    def _position_in_steps(self):
        """
        Retreive the current position in steps.

        Returns
        -------
        current_position : int
            The absolute position to travel to in units of steps.

        Raises
        ------
        NotImplementedError
            If _position_in_steps has not been overridden with an
            implementation specific function.

        Notes
        -----
        Function should cooperate with _moveToTarget.
        """
        raise NotImplementedError('_position_in_steps is not overridden.')

    def _setSpeed(self, speed: int):
        self._steps_per_second = speed

    def _typeSorter(self, type: str):
        """Convert string to enum."""
        if type in ('steps', 'Steps'):
            return self._unit_type['STEPS']
        elif type in ('units', 'Units'):
            return self._unit_type['UNITS']
        else:
            warnings.warn("Expected `units` or `steps`.")
            return self._unit_type['UNKNOWN']

    def _checkMicrostep(self, microstep: int):
        """Check validity of microstep input."""
        if microstep in (1, 2, 4, 8, 16):
            return 1
        else:
            return 0

    def _setMicrostep(self, microstep: int):
        """
        Set motor driver microstepping to the indicated value.

        Parameters
        ----------
        microstep : int
            The number of microsteps per full step.

        Warnings
        --------
        UserError
            If _setMicrostep has not been overridden with an
            implementation specific function.
        """
        self._microsteps_per_full_step = microstep
        warnings.warn("Overload _setMicrostep for functionality.")

    def _convUnitsToSteps(self, units):
        return units / self.units_per_step

    def _convStepsToUnits(self, steps):
        return steps * self.units_per_step

    def _convReltoAbs(self, rel_steps):
        return self.position('steps') + rel_steps

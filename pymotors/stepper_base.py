"""General purpose stepper motor base class."""
import warnings


class StepperBase():
    """Stepper motor base class.

    Base class for interfacing with stepper motors while being agnostic to
    implementation specifics. Provides movement commands in absolute and
    relative positions described in steps or units per step.

    Attributes
    ----------
    microsteps : int
        Ratio of full steps to microsteps.
    dist_per_rev : float
        Conversion factor converting steps into user defined units.
    steps_per_second : float
        Stepper speed in steps
    rpm : float
        Stepper speed in user defined units.
    enable : bool
        Software lock on stepper motion.

    Notes
    -----
    If using `units`, set microsteps before dist_per_rev if using microsteps.
    Set dist_per_rev before rpm.

    """

    # pylint: disable=invalid-name
    # pylint: disable=too-many-instance-attributes

    _enable_states = {'DISABLED': False, 'ENABLED': True}
    _unit_type = {'UNKNOWN': -1, 'STEPS': 0, 'DIST': 1}

    def __init__(self, dist_per_rev=1, steps_per_rev=200, rpm=1):
        self._enable = None
        self._steps_per_second = None
        self._target_steps = 0
        self._microsteps_per_full_step = 1
        self.steps_per_rev = steps_per_rev
        self.dist_per_rev = dist_per_rev
        self.rpm = rpm
        self.enable = self._enable_states['DISABLED']

    @property
    def microsteps(self) -> float:
        """Fraction of a stepper motor full step per pulse."""
        return 1 / self._microsteps_per_full_step

    @microsteps.setter
    def microsteps(self, step_ratio: float):
        micros_per_full_step = 1 / step_ratio
        if self._checkMicrostep(micros_per_full_step):
            old_micros = self.microsteps
            new_to_old = micros_per_full_step / old_micros
            self.rpm = self.rpm * new_to_old  # reset RPM for new micros
            self._setMicrostep(micros_per_full_step)
        else:
            warnings.warn("Microstep value not available.")

    @property
    def dist_per_min(self):
        """Speed in distance per minute."""
        return round(self._convStepsToDist(self._steps_per_second) * 60, 3)

    @dist_per_min.setter
    def dist_per_min(self, speed: float):
        if speed > 0:
            steps_per_second = self._convDistToSteps(speed / 60)
            self._setSpeed(steps_per_second)
            self._steps_per_second = steps_per_second
        else:
            warnings.warn("Speed must be greater than 0.")

    @property
    def rpm(self) -> float:
        """Speed in revolutions per minute."""
        rpm = self.dist_per_min / self.dist_per_rev
        return round(rpm, 3)

    @rpm.setter
    def rpm(self, revs_per_min: float):
        """Set dist_per_rev before calling rpm."""
        if revs_per_min > 0:
            self.dist_per_min = revs_per_min * self.dist_per_rev
        else:
            warnings.warn("Speed must be greater than 0.")

    @property
    def enable(self) -> bool:
        """Enable or disable the motor."""
        return self._enable

    @enable.setter
    def enable(self, state):
        """
        Enable or disable the motor.

        Parameters
        ----------
        state : bool
            The desired motor state.

        Notes
        -----
        Can be overridden to apply implementation specific hardware enabling.

        """
        if state == self._enable_states['DISABLED']:
            self._enable = self._enable_states['DISABLED']
        elif state == self._enable_states['ENABLED']:
            self._enable = self._enable_states['ENABLED']
        else:
            warnings.warn('Expected `False` (disabled) or `True` (enable)')

    def moveAbsSteps(self, target_steps: int):
        """Move to target step position."""
        if self._enable:
            self._target_steps = target_steps
            self._moveToTarget()
        else:
            warnings.warn("Motor is not enable and cannot move.")

    def moveRelSteps(self, rel_target_steps: int):
        """Move target steps away from current position."""
        target_steps = round(self._convReltoAbs(rel_target_steps))
        self.moveAbsSteps(target_steps)

    def moveAbsDist(self, target_dist: float):
        """Move to target unit position."""
        target_steps = round(self._convDistToSteps(target_dist))
        self.moveAbsSteps(target_steps)

    def moveRelDist(self, rel_target_dist: float):
        """Move target dist away from current position."""
        rel_target_steps = self._convDistToSteps(rel_target_dist)
        self.moveRelSteps(rel_target_steps)

    def position(self, val_type: str):
        """Return current position in steps or dist.

        Parameters
        ----------
        type : str
            The desired interpretation of the current position.

        Returns
        -------
        position : int
            Position in either absolute dist or absolute steps.

        """
        output_type = self._typeSorter(val_type)
        if output_type == self._unit_type['STEPS']:
            ret = self._position_in_steps()
        elif output_type == self._unit_type['DIST']:
            ret = self._convStepsToDist(self._position_in_steps())
        return ret

    def isMoving(self):
        """Motor has not arrived at commanded position."""
        return self.position('steps') != self._target_steps

    def stop(self):
        """Set position to target position.

        Stops movement by setting current position to target position. Also,
        disable the motor to ignore queued movement commands.
        """
        self.moveRelSteps(0)

    def _moveToTarget(self):
        """
        Step the motor towards the target position.

        Parameters
        ----------
        target_position : int
            The absolute position to travel to in dist of steps.

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
        Function should account for _accel and _decel when implemented.
        """
        raise NotImplementedError('_moveTo is not overridden.')

    def _position_in_steps(self):
        """
        Retreive the current position in steps.

        Returns
        -------
        current_position : int
            The absolute position to travel to in dist of steps.

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

    def _typeSorter(self, val_type: str) -> int:
        """Convert string to enum."""
        ret = self._unit_type['UNKNOWN']
        if val_type in ('steps', 'Steps'):
            ret = self._unit_type['STEPS']
        elif val_type in ('dist', 'Dist'):
            ret = self._unit_type['DIST']
        else:
            warnings.warn("Expected `dist` or `steps`.")
        return ret

    @staticmethod
    def _checkMicrostep(microstep: int):
        """Check validity of microstep input."""
        ret = 0
        if microstep in (1, 2, 4, 8, 16):
            ret = 1
        return ret

    def _setMicrostep(self, microstep: int):
        """
        Set motor driver microstepping to the indicated value.

        Parameters
        ----------
        microstep : int
            The number of microsteps per full step.

        """
        self._microsteps_per_full_step = microstep
        warnings.warn("Overload _setMicrostep for functionality.")

    def _convDistToSteps(self, dist) -> float:
        return dist * self._micros_per_dist()

    def _convStepsToDist(self, steps) -> float:
        return steps / self._micros_per_dist()

    def _convReltoAbs(self, rel_steps):
        return self.position('steps') + rel_steps

    def _micros_per_dist(self) -> float:
        steps_per_dist = self.steps_per_rev / self.dist_per_rev
        microsteps_per_dist = steps_per_dist * self._microsteps_per_full_step
        return microsteps_per_dist

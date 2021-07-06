# -*- coding: utf-8 -*-
"""
Created on Tue Jul 16 10:00:27 2019

Purpose: This class implements application-specific functionality as an extension
of the TicStepper class, which it receives as input. Here the user can define custom positions such as both
forward and reverse limit switch positions, soft limits, as well as other user-
defined positions.

This class uses the TicStepper class to keep track of rotational position
(in steps) and velocity (in steps/second). A user can also use this class to
define custom user preset positions.

A future version will implement conversion to linear distance.

Note: CURRENTLY, ONLY DUAL LIMIT SWITCH BEHAVIOR HAS BEEN TESTED!

@author: paul.lebel
Date: 2019/07/16

Update 2019/8/7: as of today, only tic T500 boards have been tested with this class.
"""

import warnings
from time import sleep, time
from .tic_stepper import TicStepper

# ---------------------------------------CONSTANTS-----------------------------------------------
_SOFTLIMIT_BUFFER_STEPS = 20
_DEF_MAX_HOMING_STEPS = 1E8
_TIC_FWD_LIMIT_BIT = 2
_TIC_REV_LIMIT_BIT = 3
_DEF_HOME_SPD_STEPS_PER_SEC = 50    # Default homing speed
_DEF_MAX_SPD_STEPS_PER_SEC = 500     # If microstepping, refers to microsteps/second
_WFM_PAUSE = 0.01
_TOLERANCE_EXCEPTION_TIMEOUT = 0.05
_MAX_ALLOWABLE_TOLERANCE = 5
_SLEEP_BEFORE_HOMING_S = 1.5
_HOMING_WAIT_TIME = 0.2
_IDENTITY = 'TicStage'

# ---------------------------------------SET ON INSTANTIATION-----------------------------------------------
_MOTION_TOL_STEPS = 3

# -----------------------------------------------------------------------------------------------

# ---------------------------------------METHODS-------------------------------------------------
class TicStage(TicStepper):
    """Extends TicStepper base class to implement functionality specifically for use with a translation stage.
    
    This class, TicStage, allows a user to define custom positions for both forward
    and reverse limit switch positions, soft limits, and other user-defined 
    positions. 

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

    max_speed : int
        Set the maximum allowed speed of the motor.

    micro_step_factor : float
        Ratio of full steps to microsteps.

    default_step_tol : int
        Sets the default step tolerance for all motions (can be overriden by passing 
        a step tolerance parameter whenever calling a motion function)
    """

    def __init__(self, com_type: str,
                 port_params,
                 address=None,
                 input_dist_per_rev=1,
                 input_steps_per_rev=200,
                 input_rpm=1,
                 max_speed = _DEF_MAX_SPD_STEPS_PER_SEC, 
                 micro_step_factor=1,
                 default_step_tol=_MOTION_TOL_STEPS):
        super().__init__(com_type, port_params, address, input_dist_per_rev, input_steps_per_rev, input_rpm)
        
        try:
            self._fwd_sw_present = self.checkLimitSwitch('fwd')
            self._rev_sw_present = self.checkLimitSwitch('rev')
            self.microsteps = 1/micro_step_factor
            self._micro_step_factor = micro_step_factor
            self.motion_tol_steps = default_step_tol
            self.disable()
        except Exception as e:
            print('Failed to read properties from TicStepper object')
            print(e)
            return

        # Initialize values for limit switch positions and motion range
        self._fwd_lim_sw_position_tic = float('nan')
        self._rev_lim_sw_position_tic = float('nan')
        self._allowed_motion_range = [0,0]
        self._index_positions = dict()
        self._max_speed_steps_per_second = max_speed

        return

    def clearIndexedPositions(self):
        """Clears the indexed position dictionary"""

        self._index_positions = dict()

    def disable(self):
        """De-energizes the stepper motor. After this happens, position
        certainty is no longer valid, and therefore the motion range.
        
        Returns
        -------
        Flag indicating success/failure
        """

        self._is_motion_range_known = False
        self._allowed_motion_range = [0,0]

        try:
            self.enable = False
        except Exception as e:
            print('Error disabling the stage!')
            print(e)
            return False

        return True
    
    def discoverMotionRange(self, max_steps = _DEF_MAX_HOMING_STEPS, timeout_s = 60) -> bool:
        """Automates bi-directional homing process

        Parameters
        ----------
        max_steps : int
            The maximum number of steps to take while searching for the limit switch
        timeout_s : float 
            The maximum amount of time to spend looking for the limit switch
        Returns
        -------
        Flag (bool) indicating success/failure
        """

        if not self.enable:
            print('Motor is not enabled - returning.')
            return False

        # Check limit switches
        if (not self._fwd_sw_present) and (not self._rev_sw_present):
            print('At least one limit switch must be configured to discover motion range! Returning.')
            return False

        # Move the motor in the forward direction until the limit switch is encountered
        if self._fwd_sw_present:
            try:
                self.moveToLimit('fwd', max_steps, timeout_s)
            except Exception as e:
                self.enable = False
                print("Unable to find the forward home switch")
                print(e)
                return False

            fwd_pos = self.getCurrentPositionSteps()
        else:
            fwd_pos = float('inf')

        # Next, home in the reverse direction. Once the limit switch is encountered,
        # the TicStepper position and the TicStage position will be set to zero.
        if self._rev_sw_present:
            try:
                rev_lim_achieved = self.moveToLimit('rev', max_steps, timeout_s)
            except Exception as e:
                self.enable = False
                print("Could not complete home reverse routine. Disabling TicStepper")
                print(e)
                return False

            if not rev_lim_achieved:
                print('Stage did not find the reverse limit switch')
                return False

            rev_pos = self.getCurrentPositionSteps()
        else:
            rev_pos = -float('inf')

        # Home the TicStepper, as this will set its current position to 0.
        # Homing takes 20 ms to set the byte (See step 4: https://www.pololu.com/docs/0J71/5.6)
        self.home('rev')
        sleep(_HOMING_WAIT_TIME)

        self._rev_lim_sw_position_tic = 0
        self._fwd_lim_sw_position_tic = fwd_pos - rev_pos
        self._is_motion_range_known = True
        self._updateAllowedMotionRange()
        print('Motion range discovered.')

        return True


    def getIndexedPositions(self):
        return self._index_positions

    def getMotionRange(self):
        """Returns the allowed motion range

        Returns
        -------
        A List containing motion limits
        """

        return self._allowed_motion_range

    def isLimitActive(self, limit) -> bool:
        """Check whether the specified limit switch is active or not

        Parameters
        ----------
        limit : string 
            Indicates which limit is being checked. Must be either
            'fwd' or 'rev'

        Returns
        -------
        Flag indicating switch status (limit active--> return True)
        """

        misc_resp, _, _ = self._getmotor_status()
        if limit == 'fwd':
            return bool(misc_resp[0] & 2**_TIC_FWD_LIMIT_BIT)
        if limit == 'rev':
            return bool(misc_resp[0] & 2**_TIC_REV_LIMIT_BIT)
        else:
            print('Invalid string! "limit" must be either "fwd" or "rev".')
            return False

    def isTargetValid(self, target_pos):
        """Checks whether the specified position is within the allowed motion range

        Parameters
        ----------
        target_pos : int
            Position in steps

        Returns
        -------
        : bool
            Success/failure flag
        """

        try:
            target_pos = int(target_pos)
        except:
            print('target_pos must be convertable to integer!')
            return False

        if not self._is_motion_range_known:
            print('Motion range is not known. Cannot check target validity.')
            return False

        return (target_pos >= self._allowed_motion_range[0]) and (target_pos <= self._allowed_motion_range[1])

    def moveAbsSteps(self, position_steps, wait_for_motion = True, open_loop_assert = False, 
                        step_tolerance = None, timeout = _TOLERANCE_EXCEPTION_TIMEOUT):
        """Move to an absolute position, in steps

        If the stage does not reach its target location within the specified tolerance
        (i.e it stops X steps before the target), this function will raise an exception
        which must be handled by the user.

        Parameters
        ----------
        steps : int
            Target position of proposed move, in steps

        wait_for_motion : bool
            Flag to either block execution (or not)
            while motion is in progress

        open_loop_assert : bool
            If true, the motion will be performed whether or not
            there is a motion range defined.

        step_tolerance : int
            The desired step tolerance for the motion. If none, the default step tolerance 
            (set during instantiation) will be used. Otherwise the provided step tolerance 
            will be used.

        timeout : float
            Specifies the time (in s) before raising an error 
            if the motor does not arrive to the target location within the specified tolerance. 
            Defaults to 0.05s.

        Returns
        -------
        Success/failure flag
        """
        
        tolerance = step_tolerance if step_tolerance is not None else self.motion_tol_steps

        if self._is_motion_range_known:
            if self.isTargetValid(position_steps):
                super()._moveAbsSteps(position_steps)
                if wait_for_motion:
                    self.wait_for_motion(motion_tol_steps=tolerance, timeout=timeout)
                return True
            else:
                print('Proposed motion is out of range - returning without motion.')
                return False
        elif open_loop_assert:
            super()._moveAbsSteps(position_steps)
            if wait_for_motion:
                self.wait_for_motion(motion_tol_steps=tolerance, timeout=timeout)
            return True
        else:
            print('Motion range not known. If you wish to move anyway, please set "open_loop_assert" argument to "True".')
            return False

    def moveRelSteps(self, steps, wait_for_motion=True, open_loop_assert=False, step_tolerance=None, 
                        timeout=_TOLERANCE_EXCEPTION_TIMEOUT) -> bool:
        """Move a specified number of steps relative to the current position

        If the stage does not reach its target location within the specified tolerance
        (i.e it stops X steps before the target), this function will raise an exception
        which must be handled by the user.
        
        Parameters
        ----------
        steps : int
            Size of proposed move, in steps

        wait_for_motion : bool 
            Flag to either block execution (or not)
            while motion is in progress

        open_loop_assert : bool 
            If true, the motion will be performed whether or not
            there is a motion range defined.

        step_tolerance : int
            The desired step tolerance for the motion. If none, the default step tolerance 
            (set during instantiation) will be used. Otherwise the provided step tolerance 
            will be used.

        timeout : float
            Specifies the time (in s) before raising an error 
            if the motor does not arrive to the target location within the specified tolerance. 
            Defaults to 0.05s.

        Returns
        -------
        Success/failure flag
        """
        
        tolerance = step_tolerance if step_tolerance is not None else self.motion_tol_steps

        if self._is_motion_range_known:
            if self.isTargetValid(steps + self.getCurrentPositionSteps()):
                super()._moveRelSteps(steps)
                if wait_for_motion:
                    self.wait_for_motion(motion_tol_steps=tolerance, timeout=timeout)
                return True
            else:
                print('Proposed motion is out of range. Please try a smaller move.')
                return False
        elif open_loop_assert:
            super()._moveRelSteps(steps)
            if wait_for_motion:
                    self.wait_for_motion(motion_tol_steps=tolerance, timeout=timeout)
            return True
        else:
            print('Motion range not known. If you wish to move anyway, please set "open_loop_assert" to "True".')
            return False

    def moveToIndexedPosition(self, index, wait=True, open_loop_assert=False, step_tolerance=None, 
                                timeout=_TOLERANCE_EXCEPTION_TIMEOUT):
        """Moves the stage to the specified indexed position.
        
        Parameters
        ----------
        indices : int / int list
            One or more (can be any iterable?) key to the indexed
            position dictionary (see setIndexedPositions() method). If an interable
            is provided, the stage will go to each indexed position sequentially.

        wait : bool
            Flag whether to block command line during motion or not
        
        step_tolerance : int
            The desired step tolerance for the motion. If none, the default step tolerance 
            (set during instantiation) will be used. Otherwise the provided step tolerance 
            will be used.

        timeout : float
            Specifies the time (in s) before raising an error 
            if the motor does not arrive to the target location within the specified tolerance. 
            Defaults to 0.05s.

        Returns
        -------
        Success/failure flag
        """
        
        tolerance = step_tolerance if step_tolerance is not None else self.motion_tol_steps

        if index in list(self._index_positions.keys()):
            self.moveAbsSteps(self._index_positions[index], wait, open_loop_assert=open_loop_assert,
                                step_tolerance=tolerance, timeout=timeout)
        else:
            print('Index not valid!')
            return False

        return True

    def moveToLimit(self, limit: str, max_steps = _DEF_MAX_HOMING_STEPS, timeout_s = 60) -> bool:
        """Move to either the forward or reverse limit switch position.
        
        Parameters
        ----------
        limit : string
            String indicating direction: either 'fwd' or 'rev'
        max_steps : int
            The maximum number of steps to take while searching for the limit switch
        timeout_s : int 
            The maximum amount of time to spend looking for the limit switch
        
        Returns
        -------
            Success/failure flag
        """

        if not self.enable:
            print('Motor is not enabled - returning.')
            return False

        if limit == 'fwd':
            if not self._fwd_sw_present:
                print('No forward limit switch configured. Returning.')
                return False
            else:
                target_pos = abs(max_steps)
        elif limit == 'rev':
            if not self._rev_sw_present:
                print('No reverse limit switch configured. Returning.')
                return False
            else:
                target_pos = -abs(max_steps)
        else:
            print('Argument "limit" must be either "fwd" or "rev".')
            return False

        print('Homing in the ' + limit + ' direction in ' + str(_SLEEP_BEFORE_HOMING_S) + ' seconds...')
        sleep(_SLEEP_BEFORE_HOMING_S)

        # Set default homing speed, accounting for microstepping factor
        self.setRotationSpeed(_DEF_HOME_SPD_STEPS_PER_SEC*self._micro_step_factor)
        elapsed_time = 0
        initial_position = self.getCurrentPositionSteps()
        current_position = initial_position
        # Start moving, and poll the TicStepper limit switch during motion
        t1 = time()
        super()._moveRelSteps(target_pos)

        # During the motion:
        #   - Check how many steps have been issued
        #   - How much time has gone by
        #   - If the limit switch has been reached
        limit_active = False
        
        while (elapsed_time < timeout_s) and \
        (abs(current_position - initial_position) < abs(max_steps)) and not \
        limit_active:
            current_position = self.getCurrentPositionSteps()
            elapsed_time = time() - t1
            limit_active = self.isLimitActive(limit)
            sleep(_WFM_PAUSE)

        return True

    def setCurrentPositionAsIndex(self, index)->bool:
        """This method will get the current stage position, then try to
        add it to the indexed positions dictionary.

        Parameters
        ----------
        index : int
            Key to assign to the current stage position

        Returns
        -------
        bool indicating success (True) or failure (False)
        """

        if index in self._index_positions.keys():
            print('Warning - overwriting existing index')

        # Get current position
        pos = self.getCurrentPositionSteps()

        # Call existing class method
        flag = self.setIndexedPositions({index: pos})

        return flag

    def setIndexedPositions(self, position_map)->bool:
        """User provides a dictionary mapping indices (keys) to stage
        positions (steps). This method will update the dictionary depending on
        whether the positions provided are valid. If there is no motion range
        defined, then the validity check is not performed.

        Parameters
        ----------
        position_map : dict
            A dictionary mapping indices (keys) to stage positions
            (steps)

        Returns
        -------
        bool indicating success (True) or failure (False)
        """

        if type(position_map) != dict:
            print('Please provide a dict() - returning.')
            return False

        if self._is_motion_range_known:
            vals = list(position_map.values())
            for v in vals:
                if not self.isTargetValid(v):
                    print('One of the positions is out of motion range!')
                    return False
            try:
                self._index_positions.update(position_map)
            except Exception as e:
                print('Could not set the indexed positions')
                print(e)
                return False
        else:
            # There is no known motion range
            try:
                self._index_positions.update(position_map)
            except Exception as e:
                print('Could not set the indexed positions')
                print(e)
                return False

        return True

    def setRotationSpeed(self, steps_per_second) -> bool:
        """Sets the rotation speed of the motor.
        
        Parameters
        ----------
        steps_per_second : int
            Desired speed of the motor
        
        Returns
        -------
        Success/failure flag
        """

        try:
            _ = int(steps_per_second)
        except:
            print('Input must be a number!')
        
        if steps_per_second > self._max_speed_steps_per_second:
            print('steps_per_second is too large!')
            return False

        try:
            self.rpm = 60*steps_per_second/(self.steps_per_rev*self._micro_step_factor)
        except Exception as e:
            print("Could not set TicStepper RPMs")
            print(e)
            return False

        self._steps_per_second = steps_per_second
        return True

    def print(self):
        """Extending parent print to add TicStage specific diagnostics"""

        super().print()
        print('Forward limit switch present: ' + str(self._fwd_sw_present))
        print('Reverse limit switch present: ' + str(self._rev_sw_present))
        print('Motion range known: ' + str(self._is_motion_range_known))
        print(f'Motion range: [{self._allowed_motion_range[0]},{self._allowed_motion_range[1]}]')
        print('Current position (steps): ' + str(self.getCurrentPositionSteps()))
        print(f"Step tolerance: {self.motion_tol_steps} \n")
        
    def type(self):
        # Overloading type method to return a simplified string
        return _IDENTITY

    def _updateAllowedMotionRange(self) -> bool:
        """Defines range of allowed positions, including the soft limit
        buffer. Motion range must be known, otherwise allowed range cannot be set.
        
        Returns
        -------
        Success/failure flag
        """

        if self._is_motion_range_known:
            self._allowed_motion_range[0] = self._rev_lim_sw_position_tic + _SOFTLIMIT_BUFFER_STEPS
            self._allowed_motion_range[1]  = self._fwd_lim_sw_position_tic - _SOFTLIMIT_BUFFER_STEPS
            return True
        else:
            print('Motion range is not known. Cannot set known motion range!')
            self._allowed_motion_range[0] = 0
            self._allowed_motion_range[1] = 0
            return False

    def wait_for_motion(self, motion_tol_steps, timeout):
        """Blocks execution until the stage reaches its target
        
        If the stage does not reach its target location within the specified tolerance
        (i.e it stops X steps before the target), this function will raise an exception
        which must be handled by the user.

        Parameters
        ----------
        motion_tol_steps : int
            Tolerance in number of steps between motor position and desired position
            
        timeout : float
            Specifies the time (in s) before raising an error 
            if the motor does not arrive to the target location within the specified tolerance. 
            Defaults to 0.05s.
        
        """

        # Additional tolerance that will only be checked if a timeout is specified
        # This is to prevent an infinite loop in case the motor gets stuck
        num_prev_to_keep = 10
        prev_positions = [None] * num_prev_to_keep
        is_stuck = False

        print('TicStage: In motion...')
        sleep(_WFM_PAUSE)

        # Bring motor to within the desired number of tolerance steps
        while abs(self.getCurrentPositionSteps() - self._target_steps) > motion_tol_steps:
            sleep(_WFM_PAUSE)

            if (motion_tol_steps < abs(self.getCurrentPositionSteps() - self._target_steps) < _MAX_ALLOWABLE_TOLERANCE):

                # Manual method of checking if motor is stopped
                prev_positions.append(self.getCurrentPositionSteps())
                prev_positions = prev_positions[-num_prev_to_keep:]

                if ( prev_positions.count(prev_positions[0]) == len(prev_positions) ) and not is_stuck: 
                    start_time = time()
                    is_stuck = True

                if is_stuck and (time() - start_time) > timeout:
                    raise Exception(f"Did not reach the specified position {self._target_steps} within the desired tolerance {motion_tol_steps}.")
        
        sleep(_WFM_PAUSE*5)
        print(f"Destination: \t{self._target_steps}")
        print(f"Actual: \t{self.getCurrentPositionSteps()}")

    def __del__(self):
        """Ensures the stage is disabled upon deletion of the object"""
        
        self.disable()
        return
# --------------------------------------------------------------------------------------------------


# ---------------------------------------PROPERTIES-------------------------------------------------
    @property
    def indexedPositions(self) -> dict:
        return self._index_positions
# --------------------------------------------------------------------------------------------------

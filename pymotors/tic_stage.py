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

from time import sleep, time
from .tic_stepper import TicStepper

# ---------------------------------------CONSTANTS-----------------------------------------------
_SOFTLIMIT_BUFFER_STEPS = 20
_DEF_MAX_HOMING_STEPS = 1E8
_DEF_MOVE_TIMEOUT_S = 1000
_TIC_FWD_LIMIT_BIT = 2
_TIC_REV_LIMIT_BIT = 3
_DEF_HOME_SPD_STEPS_PER_SEC = 50    # Default homing speed
_DEF_MAX_SPD_STEPS_PER_SEC = 500     # If microstepping, refers to microsteps/second
_WFM_PAUSE = 0.01
_MOTION_TOL_STEPS = 3
_SLEEP_BEFORE_HOMING_S = 3
_IDENTITY = 'TicStage'

# -----------------------------------------------------------------------------------------------

# ---------------------------------------METHODS-------------------------------------------------
class TicStage(TicStepper):
    """Extends TicStepper base class to implement an application-specific class (TODO: What sort of application? Need to elaborate).
    
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
    """

    def __init__(self, com_type: str,
                 port_params,
                 address=None,
                 input_dist_per_rev=1,
                 input_steps_per_rev=200,
                 input_rpm=1,
                 max_speed = _DEF_MAX_SPD_STEPS_PER_SEC, 
                 micro_step_factor=1):
        TicStepper.__init__(com_type, port_params, address, input_dist_per_rev, input_steps_per_rev, input_rpm)
    

        try:
            self._fwd_sw_present = self.checkLimitSwitch('fwd')
            self._rev_sw_present = self.checkLimitSwitch('rev')
            self.microsteps = 1/micro_step_factor
            self._micro_step_factor = micro_step_factor
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

    def discoverMotionRange(self, max_steps = 1E8, timeout_s = 60) -> bool:
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

            fwd_pos = self.position('steps')
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

            rev_pos = self.position('steps')
        else:
            rev_pos = -float('inf')

        # Home the TicStepper, as this will set its current position to 0
        self.home('rev')
        self._rev_lim_sw_position_tic = 0
        self._fwd_lim_sw_position_tic = fwd_pos - rev_pos
        self._is_motion_range_known = True
        self._updateAllowedMotionRange()
        print('Motion range discovered.')

        return True

    def enable(self) -> bool:
        """Set new B parameter value and recalculate f(x)
        
        Returns
        -------
        Flag (bool) indicating success/failure of enabling the motor.
        """

        try:
            self.enable = True
            self.stop()
        except Exception as e:
            print('Could not enable the TicStepper object!')
            print(e)
            return False

        return True

    def getCurrentposition_steps(self):
        return self.position('steps')

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
            target_pos : position in steps

        Returns
        -------
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

    def moveAbsSteps(self, position_steps, wait_for_motion = True, open_loop_assert = False):
        """Move to an absolute position, in steps

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
        
        Returns
        -------
        Success/failure flag
        """

        if self._is_motion_range_known:
            if self.isTargetValid(position_steps):
                self.moveAbsSteps(position_steps)
                if wait_for_motion:
                    self.wait_for_motion()
                return True
            else:
                print('Proposed motion is out of range - returning without motion.')
                return False
        elif open_loop_assert:
            self.moveAbsSteps(position_steps)
            if wait_for_motion:
                self.wait_for_motion()
            return True
        else:
            print('Motion range not known. If you wish to move anyway, please set "open_loop_assert" argument to "True".')
            return False

    def moveRelSteps(self, steps, wait_for_motion = True, open_loop_assert = False) -> bool:
        """Move a specified number of steps relative to the current position
        
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
        
        Returns
        -------
            Success/failure flag
        """

        if self._is_motion_range_known:
            if self.isTargetValid(steps + self.position('steps')):
                self.moveRelSteps(steps)
                if wait_for_motion:
                    self.wait_for_motion()
                return True
            else:
                print('Proposed motion is out of range. Please try a smaller move.')
                return False
        elif open_loop_assert:
            self.moveRelSteps(steps)
            if wait_for_motion:
                    self.wait_for_motion()
            return True
        else:
            print('Motion range not known. If you wish to move anyway, please set "open_loop_assert" to "True".')
            return False

    def moveToIndexedPosition(self, index, wait=True, open_loop_assert=False):
        """Moves the stage to the specified indexed position.
        
        Parameters
        ----------
        indices : int / int list
            One or more (can be any iterable?) key to the indexed
            position dictionary (see setIndexedPositions() method). If an interable
            is provided, the stage will go to each indexed position sequentially.

        wait : bool
            Flag whether to block command line during motion or not

        Returns
        -------
            Success/failure flag
        """

        if index in list(self._index_positions.keys()):
            self.moveAbsSteps(self._index_positions[index], wait, open_loop_assert=open_loop_assert)
        else:
            print('Index not valid!')
            return False

        return True

    def moveToLimit(self, limit: str, max_steps=1E8, timeout_s = 60) -> bool:
        """Move to either forward or reverse limit switch position.
        
        Parameters
        ----------
        limit : string
            string indicating direction: either 'fwd' or 'rev'
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
        initial_position = self.position('steps')
        current_position = initial_position
        # Start moving, and poll the TicStepper limit switch during motion
        t1 = time()
        self.moveRelSteps(target_pos)

        # During the motion:
        #   - Check how many steps have been issued
        #   - How much time has gone by
        #   - If the limit switch has been reached
        limit_active = False
        while (elapsed_time < timeout_s) and \
        (abs(current_position - initial_position) < abs(max_steps)) and not \
        limit_active:
            current_position = self.position('steps')
            #print('Current position = ' + str(current_position))
            elapsed_time = time() - t1
            limit_active = self.isLimitActive(limit)
            #print('Limit active: ' + str(limit_active))
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
        pos = self.getCurrentposition_steps()

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
        """Sets the rotation speed of the motor
        
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

    def wait_for_motion(self, motion_tol_steps = _MOTION_TOL_STEPS):
        """Blocks execution until the stage reaches its target"""

        print('TicStage: In motion...')
        sleep(_WFM_PAUSE)
        while abs(self.getCurrentposition_steps() - self._target_steps) > motion_tol_steps:
            #print('In motion....' + str(self._ticStepper.isMoving()))
            sleep(_WFM_PAUSE)

    def __del__(self):
        """Ensures the stage is disabled upon deletion of the object"""
        
        self.disable()
        del(self._ticStepper)
        return
# --------------------------------------------------------------------------------------------------


# ---------------------------------------PROPERTIES-------------------------------------------------
    @property
    def indexedPositions(self) -> dict:
        return self._index_positions
# --------------------------------------------------------------------------------------------------

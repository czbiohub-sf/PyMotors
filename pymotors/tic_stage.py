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

# ---------------------------------------CONSTANTS-----------------------------------------------
_OBJECT_TYPE = "TicStage"
_SOFTLIMIT_BUFFER_STEPS = 0
_DEF_MAX_HOMING_STEPS = 1E8
_DEF_MOVE_TIMEOUT_S = 1000
_MAX_RESP_BITS = 8
_TIC_FWD_LIMIT_BIT = 2
_TIC_REV_LIMIT_BIT = 3
_DEF_HOME_SPD_STEPS_PER_SEC = 50    # Default homing speed
_DEF_MAX_SPD_STEPS_PER_SEC = 500     # If microstepping, refers to microsteps/second
_WFM_PAUSE = 0.01
_MOTION_TOL_STEPS = 3
_SLEEP_BEFORE_HOMING_S = 0.5
_IDENTITY = 'TicStage'

# Uses bit flags
_errorStatusDict = {
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
_miscBitDict = {
        0: "Energized",
        1: "Position uncertain",
        2: "Forward limit active",
        3: "Reverse limit active",
        4: "Homing active"}

# Uses a map from integer to status string
_opStateDict = {
        0: "Reset",
        2: "De-engergized",
        4: "Soft error",
        6: "Waiting for ERR line",
        8: "Starting up",
        10: "Normal"}
# -----------------------------------------------------------------------------------------------

# ---------------------------------------METHODS-------------------------------------------------
class TicStage():

    def __init__(self, ticStepper, maxSpeed = _DEF_MAX_SPD_STEPS_PER_SEC, microStepFactor = 1):
        """
        Purpose: Class constructor internalizes the TicStepper object, reads
        properties from it, then starts up in a disabled mode.

        Input:
            ticStepper: Instance of TicStepper object, connected to a tic stepper
            controller board.

            maxSpeed:Set the maximum allowed speed of the motor

        Output:
            Flag indicating success/failure of the constructor

        """

#        if type(ticStepper) != 'TicStepper':
#            print('"ticStepper" must be a "TicStepper" instance!')
#            return False
#
        self._ticStepper = ticStepper

        try:
            self._fwdSwPresent = self._ticStepper.checkLimitSwitch('fwd')
            self._revSwPresent = self._ticStepper.checkLimitSwitch('rev')
            self._ticStepper.microsteps = 1/microStepFactor
            self._microStepFactor = microStepFactor
            self.disable()
        except Exception as e:
            print('Failed to read properties from TicStepper object')
            print(e)
            return

        # Initialize values for limit switch positions and motion range
        self._fwdLimSwPositionTic = float('nan')
        self._revLimSwPositionTic = float('nan')
        self._allowedMotionRange = [0,0]
        self._indexedPositions = dict()
        self._maxSpeedStepsPerSecond = maxSpeed

        return

    def clearIndexedPositions(self):
        """
        Purpose: as name suggests, it clears the indexed position dictionary
        Inputs: None
        Outputs: None
        """
        self._indexedPositions = dict()

    def disable(self):
        """
        Purpose: De-energizes the stepper motor. After this happens, position
        certainty is no longer valid, and therefore the motion range.
        Inputs: None
        Output: Flag indicating success/failure
        """

        self._isMotionRangeKnown = False
        self._allowedMotionRange = [0,0]

        try:
            self._ticStepper.enable = False
        except Exception as e:
            print('Error disabling the stage!')
            print(e)
            return False

        return True

    def discoverMotionRange(self, maxSteps = 1E8, timeout_s = 60) -> bool:
        """
        Purpose: Automates bi-directional homing process
        Inputs:
            maxSteps: the maximum number of steps to take while searching for the limit switch
            timeout_s: the maximum amount of time to spend looking for the limit switch
        Output:
            Flag indicating success/failure
        """
        if not self._ticStepper.enable:
            print('Motor is not enabled - returning.')
            return False

        # Check limit switches
        if (not self._fwdSwPresent) and (not self._revSwPresent):
            print('At least one limit switch must be configured to discover motion range! Returning.')
            return False


        # Home in the reverse direction. Once the limit switch is encountered,
        # the TicStepper position and the TicStage position will be set to zero.
        # We do not perform the TicStepper home in the forward direction because
        # it will overide and set the new zero position there.
        if self._revSwPresent:
            try:
                revLimAchieved = self.moveToLimit('rev', maxSteps, timeout_s)
                print("TicStage: found reverse limit")
                self._ticStepper.home('rev')
                self._ticStepper.setCurrentPositionAs(0)
            except Exception as e:
                self._ticStepper.enable = False
                print("Could not complete home reverse routine. Disabling TicStepper")
                print(e)
                return False

            if not revLimAchieved:
                print('Stage did not find the reverse limit switch')
                return False

            revPos = self._ticStepper.position('steps')
        else:
            revPos = -float('inf')

        # Move the motor in the forward direction until the limit switch is encountered
        if self._fwdSwPresent:
            try:
                self.moveToLimit('fwd', maxSteps, timeout_s)
                print("TicStage: found reverse limit")

            except Exception as e:
                self._ticStepper.enable = False
                print("Unable to find the reverse home switch")
                print(e)
                return False

            fwdPos = self._ticStepper.position('steps')
        else:
            fwdPos = float('inf')


        self._revLimSwPositionTic = revPos
        self._fwdLimSwPositionTic = fwdPos
        self._isMotionRangeKnown = True
        self._updateAllowedMotionRange()
        print('Motion range discovered.')
        print(f"Reverse position: {revPos} \nForward position: {fwdPos}")

        return True

    def enable(self) -> bool:
        try:
            self._ticStepper.enable = True
            self._ticStepper.stop()
        except Exception as e:
            print('Could not enable the TicStepper object!')
            print(e)
            return False

        return True

    def getAndParseMotorStatus(self)-> dict:
        # Gets all the status reports from the motor and translates them into
        # english for printing/display

        # Poll the motor for statuses
        miscResp, errResp, opResp = self._getMotorStatus()

        # Parse the responses
        miscMsg = list()
        opMsg = list()
        errMsg = list()
        for i in range(_MAX_RESP_BITS):
            if miscResp[0] & 2**i:
                miscMsg.append(_miscBitDict[i])
            # opResp format is not a bit lookup - they are just even integers
            if opResp[0] == 2*i:
                opMsg.append(_opStateDict[2*i])
            if errResp[0] & 2**i:
                errMsg.append(_errorStatusDict[i])

        motorStatus = {'OperationStatus': opMsg, \
                       'ErrorStatus': errMsg, \
                       'PositionStatus': miscMsg}

        return motorStatus

    def getCurrentPositionSteps(self):
        return self._ticStepper.position('steps')

    def getIndexedPositions(self):
        return self._indexedPositions

    def getMotionRange(self):
        """
        Purpose: Returns the allowed motion range
        Inputs: None
        Outputs: List containing motion limits
        """
        return self._allowedMotionRange

    def _getMotorStatus(self) -> tuple:
        """
        Purpose: Poll the tic flag for position certainty
        Inputs: None
        Output: tuple with the various tic stage status responses.
                If an error occurs, returns False, False, False
                See getAndParseMotorStatus() for parsed output.
        """
        try:
            miscResp = self._ticStepper.com.send(self._ticStepper._command_dict['gVariable'], self._ticStepper._variable_dict['misc_flags1'])
            errResp = self._ticStepper.com.send(self._ticStepper._command_dict['gVariable'], self._ticStepper._variable_dict['error_status'])
            opResp = self._ticStepper.com.send(self._ticStepper._command_dict['gVariable'], self._ticStepper._variable_dict['operation_state'])
        except Exception as e:
            print("Error reading motor status")
            print(e)
            return False, False, False

        return miscResp, errResp, opResp

    def isLimitActive(self, limit) -> bool:
        """
        Purpose: checks whether the specified limit switch is active or not
        Inputs:
            limit: string indicating which limit is being checked. Must be either
            'fwd' or 'rev'
        Output:
            Flag indicating switch status (limit active--> return True)
        """

        miscResp, _, _ = self._getMotorStatus()
        if limit == 'fwd':
            return bool(miscResp[0] & 2**_TIC_FWD_LIMIT_BIT)
        if limit == 'rev':
            return bool(miscResp[0] & 2**_TIC_REV_LIMIT_BIT)
        else:
            print('Invalid string! "limit" must be either "fwd" or "rev".')
            return False

    def isTargetValid(self, targetPos):
        """
        Purpose: checks whether the specified position is within the allowed motion range
        Inputs:
            targetPos: position in steps
        Output:
            Success/failure flag
        """

        try:
            targetPos = int(targetPos)
        except:
            print('targetPos must be convertable to integer!')
            return False

        if not self._isMotionRangeKnown:
            print('Motion range is not known. Cannot check target validity.')
            return False

        return (targetPos >= self._allowedMotionRange[0]) and (targetPos <= self._allowedMotionRange[1])

    def moveAbsSteps(self, positionSteps, waitForMotion = True, openLoopAssert = False):
        """
        Purpose: Move to an absolute position, in steps
        Inputs:
            steps: Target position of proposed move, in steps

            waitForMotion: as name suggests, flag to either block execution (or not)
            while motion is in progress

            openLoopAssert: If true, the motion will be performed whether or not
            there is a motion range defined.
        Outputs:
            Success/failure flag
        """
        if self._isMotionRangeKnown:
            if self.isTargetValid(positionSteps):
                self._ticStepper.moveAbsSteps(positionSteps)
                if waitForMotion:
                    self.waitForMotion()
                return True
            else:
                print('Proposed motion is out of range - returning without motion.')
                return False
        elif openLoopAssert:
            self._ticStepper.moveAbsSteps(positionSteps)
            if waitForMotion:
                self.waitForMotion()
            return True
        else:
            print('Motion range not known. If you wish to move anyway, please set "openLoopAssert" argument to "True".')
            return False

    def moveRelSteps(self, steps, waitForMotion = True, openLoopAssert = False) -> bool:
        """
        Purpose: Move a specified number of steps relative to the current position
        Inputs:
            steps: Size of proposed move, in steps

            waitForMotion: as name suggests, flag to either block execution (or not)
            while motion is in progress

            openLoopAssert: If true, the motion will be performed whether or not
            there is a motion range defined.
        Outputs:
            Success/failure flag
        """
        if self._isMotionRangeKnown:
            if self.isTargetValid(steps + self._ticStepper.position('steps')):
                self._ticStepper.moveRelSteps(steps)
                if waitForMotion:
                    self.waitForMotion()
                return True
            else:
                print('Proposed motion is out of range. Please try a smaller move.')
                return False
        elif openLoopAssert:
            self._ticStepper.moveRelSteps(steps)
            if waitForMotion:
                    self.waitForMotion()
            return True
        else:
            print('Motion range not known. If you wish to move anyway, please set "openLoopAssert" to "True".')
            return False

    def moveToIndexedPosition(self, index, wait=True, open_loop_assert=False):
        """
        Purpose: As title suggests, moves the stage to the specified indexed
        position.
        Inputs:
            indices: one or more (can be any iterable?) key to the indexed
            position dictionary (see setIndexedPositions() method). If an interable
            is provided, the stage will go to each indexed position sequentially.

            wait: Flag whether to block command line during motion or not

        Outputs:
            Success/failure flag
        """

        if index in list(self._indexedPositions.keys()):
            self.moveAbsSteps(self._indexedPositions[index], wait, openLoopAssert=open_loop_assert)
        else:
            print('Index not valid!')
            return False

        return True

    def moveToLimit(self, limit: str, maxSteps=1E8, timeout_s = 60) -> bool:
        """
        Purpose:
        Inputs:
            limit: string indicating direction: either 'fwd' or 'rev'
            maxSteps: the maximum number of steps to take while searching for the limit switch
            timeout_s: the maximum amount of time to spend looking for the limit switch
        Outputs:
            Success/failure flag
        """
        if not self._ticStepper.enable:
            print('Motor is not enabled - returning.')
            return False

        if limit == 'fwd':
            if not self._fwdSwPresent:
                print('No forward limit switch configured. Returning.')
                return False
            else:
                targetPos = abs(maxSteps)
        elif limit == 'rev':
            if not self._revSwPresent:
                print('No reverse limit switch configured. Returning.')
                return False
            else:
                targetPos = -abs(maxSteps)
        else:
            print('Argument "limit" must be either "fwd" or "rev".')
            return False

        print('Homing in the ' + limit + ' direction in ' + str(_SLEEP_BEFORE_HOMING_S) + ' seconds...')
        sleep(_SLEEP_BEFORE_HOMING_S)

        # Set default homing speed, accounting for microstepping factor
        self.setRotationSpeed(_DEF_HOME_SPD_STEPS_PER_SEC*self._microStepFactor)
        elapsedTime = 0
        initialPosition = self._ticStepper.position('steps')
        currentPosition = initialPosition
        # Start moving, and poll the TicStepper limit switch during motion
        t1 = time()
        self._ticStepper.moveRelSteps(targetPos)

        # During the motion:
        #   - Check how many steps have been issued
        #   - How much time has gone by
        #   - If the limit switch has been reached
        limitActive = False
        while (elapsedTime < timeout_s) and \
        (abs(currentPosition - initialPosition) < abs(maxSteps)) and not \
        limitActive:
            currentPosition = self._ticStepper.position('steps')
            #print('Current position = ' + str(currentPosition))
            elapsedTime = time() - t1
            limitActive = self.isLimitActive(limit)
            #print('Limit active: ' + str(limitActive))
            sleep(_WFM_PAUSE)

        return True

    def print(self):
        """
        Purpose: Print status of this object to the command line
        Inputs: None
        Outputs: None
        """
        motorStatus = self.getAndParseMotorStatus()
        print('\n------------------')
        print(_OBJECT_TYPE)
        print('------------------\n')

        print('Forward limit switch present: ' + str(self._fwdSwPresent))
        print('Reverse limit switch present: ' + str(self._revSwPresent))
        print('Motion range known: ' + str(self._isMotionRangeKnown))
        print(f'Motion range: [{self._allowedMotionRange[0]},{self._allowedMotionRange[1]}]')
        print('Current position (steps): ' + str(self.getCurrentPositionSteps()) + '\n')

        print('TicStepper attributes:')
        print('------------------\n')

        for key in motorStatus.keys():
            print(key)
            for value in motorStatus[key]:
                print('---------'+ value)

    def setCurrentPositionAsIndex(self, index)->bool:
        """
        Purpose: This method will get the current stage position, then try to
        add it to the indexed positions dictionary.

        Inputs:
            index: key to assign to the current stage position

        Output:
            bool indicating success (True) or failure (False)
        """
        if index in self._indexedPositions.keys():
            print('Warning - overwriting existing index')

        # Get current position
        pos = self.getCurrentPositionSteps()

        # Call existing class method
        flag = self.setIndexedPositions({index: pos})

        return flag

    def setIndexedPositions(self, positionMap)->bool:
        """
        Purpose: User provides a dictionary mapping indices (keys) to stage
        positions (steps). This method will update the dictionary depending on
        whether the positions provided are valid. If there is no motion range
        defined, then the validity check is not performed.

        Inputs:
            positionMap: a dictionary mapping indices (keys) to stage positions
            (steps)

        Output:
            bool indicating success (True) or failure (False)
        """
        if type(positionMap) != dict:
            print('Please provide a dict() - returning.')
            return False

        if self._isMotionRangeKnown:
            vals = list(positionMap.values())
            for v in vals:
                if not self.isTargetValid(v):
                    print('One of the positions is out of motion range!')
                    return False
            try:
                self._indexedPositions.update(positionMap)
            except Exception as e:
                print('Could not set the indexed positions')
                print(e)
                return False
        else:
            # There is no known motion range
            try:
                self._indexedPositions.update(positionMap)
            except Exception as e:
                print('Could not set the indexed positions')
                print(e)
                return False

        return True

    def setRotationSpeed(self, stepsPerSecond) -> bool:
        """
        Purpose: Sets the rotation speed of the motor
        Inputs:
            stepsPerSecond: Desired speed of the motor
        Outputs:
            Success/failure flag
        """
        try:
            _ = int(stepsPerSecond)
        except:
            print('Input must be a number!')

        if stepsPerSecond > self._maxSpeedStepsPerSecond:
            print('stepsPerSecond is too large!')
            return False

        try:
            self._ticStepper.rpm = 60*stepsPerSecond/(self._ticStepper.steps_per_rev*self._microStepFactor)
        except Exception as e:
            print("Could not set TicStepper RPMs")
            print(e)
            return False

        self._stepsPerSecond = stepsPerSecond
        return True

    def type(self):
        # Overloading type method to return a simplified string
        return _IDENTITY

    def _updateAllowedMotionRange(self) -> bool:
        """
        Purpose: Defines range of allowed positions, including the soft limit
        buffer. Motion range must be known, otherwise allowed range cannot be set.
        Inputs: None
        Outputs: Success/failure flag
        """
        if self._isMotionRangeKnown:
            self._allowedMotionRange[0] = self._revLimSwPositionTic + _SOFTLIMIT_BUFFER_STEPS
            self._allowedMotionRange[1]  = self._fwdLimSwPositionTic - _SOFTLIMIT_BUFFER_STEPS
            return True
        else:
            print('Motion range is not known. Cannot set known motion range!')
            self._allowedMotionRange[0] = 0
            self._allowedMotionRange[1] = 0
            return False

    def waitForMotion(self, motionTolSteps = _MOTION_TOL_STEPS):
        """
        Purpose: Blocks execution until the stage reaches its target
        Inputs: None
        Outputs: None
        """
        print('TicStage: In motion...')
        sleep(_WFM_PAUSE)
        while abs(self.getCurrentPositionSteps() - self._ticStepper._target_steps) > motionTolSteps:
            #print('In motion....' + str(self._ticStepper.isMoving()))
            sleep(_WFM_PAUSE)

    def __del__(self):
        """
        Purpose: Ensures the stage is disabled upon deletion of the object
        Inputs: None
        Outputs: None
        """
        del(self._ticStepper)
        return
# --------------------------------------------------------------------------------------------------


# ---------------------------------------PROPERTIES-------------------------------------------------
    @property
    def indexedPositions(self) -> dict:
        return self._indexedPositions
# --------------------------------------------------------------------------------------------------

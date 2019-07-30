# -*- coding: utf-8 -*-
"""
Created on Tue Jul 16 10:00:27 2019

Purpose: This class implements application-specific functionality as an extension
of the TicStepper class, which it receives as input. Here the user can define custom positions such as both
forward and reverse limit switch positions, soft limits, as well as other user-
defined positions. 

This class uses the TicStepper class to keep track of rotational position only 
and rotational velocity only. Conversions to linear distance and definition of 
custom user preset positions are done in this class. 

@author: paul.lebel
Date: 2019/07/16
"""

from time import sleep, time

# ---------------------------------------CONSTANTS-----------------------------------------------
_OBJECT_TYPE = "TicStage"
_SOFTLIMIT_BUFFER_STEPS = 10
_DEF_MAX_HOMING_STEPS = 1E8
_DEF_MOVE_TIMEOUT_S = 1000
_MAX_RESP_BITS = 8
_TIC_FWD_LIMIT_BIT = 2
_TIC_REV_LIMIT_BIT = 3
_DEF_HOME_SPD_STEPS_PER_SEC = 200

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

# Uses simple map from integer to status string
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
    
    def __init__(self, ticStepper):
        self._ticStepper = ticStepper
        self._fwdSwPresent = self._ticStepper.checkLimitSwitch('fwd')
        self._revSwPresent = self._ticStepper.checkLimitSwitch('rev')
        self._fwdLimSwPositionTic = float('nan')
        self._revLimSwPositionTic = float('nan')
        self._microStepFactor = self._ticStepper._microsteps_per_full_step
        self._allowedMotionRange = [0,0]
        self._indexedPositions = dict()
        self.disable()

    def clearIndexedPositions(self):
        self._indexedPositions = dict()

    def disable(self):
        self._ticStepper.enable = False
        self._isMotionRangeKnown = False
        self._allowedMotionRange = [0,0]

    def discoverMotionRange(self, maxSteps = 1E8, timeout_s = 60):
        # Inputs:
        # maxSteps: the maximum number of steps to take while searching for the limit switch
        # timeout_s: the maximum amount of time to spend looking for the limit switch
        
        if not self._ticStepper.enable:
            print('Motor is not enabled - returning.')
            return False
        
        # Check if both limit switches are present
        if not self._fwdSwPresent:
            print('No forward limit switch configured. Returning.')
            return False
        if not self._revSwPresent:
            print('No reverse limit switch configured. Returning.')
            return False

        # Move the motor in the forward direction until the limit switch is encountered
        try:
            self.moveToLimit('fwd', maxSteps, timeout_s)
        except Exception as e:
            self._ticStepper.enable = False
            print("Unable to find the reverse home switch")
            print(e)
            return False
            
        self._fwdLimSwPositionTic = self._ticStepper.position('steps')
        
        # Next, home in the reverse direction. Once the limit switch is encountered, 
        # the TicStepper position and the TicStage position will be set to zero.
        try:
            revLimAchieved = self.moveToLimit('rev', maxSteps, timeout_s)
        except Exception as e:
            self._ticStepper.enable = False
            print("Could not complete home reverse routine. Disabling TicStepper")
            print(e)
            return False
        
        if not revLimAchieved:
            print('Stage did not find the reverse limit switch')
            return False
        
        # Home the TicStepper, as this will set its current position to 0
        self._ticStepper.home('rev')
        self._revLimSwPositionTic = self._ticStepper.position('steps')
        self._isMotionRangeKnown = True
        self._updateAllowedMotionRange()
        print('Motion range discovered.')
        
        return True

    def enable(self):
        self._ticStepper.enable = True
        self._ticStepper.stop()

    def getAndParseMotorStatus(self):
        # Gets all the status reports from the motor and translates them into
        # english for printing/display
        
        # Poll the motor for statuses
        miscResp, errResp, opResp = self.getMotorStatus()
        
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
        
    def getMotorStatus(self):
        # Poll the tic flag for position certainty
        try:
            miscResp = self._ticStepper.com.send(self._ticStepper._command_dict['gVariable'], self._ticStepper._variable_dict['misc_flags1'])
            errResp = self._ticStepper.com.send(self._ticStepper._command_dict['gVariable'], self._ticStepper._variable_dict['error_status'])
            opResp = self._ticStepper.com.send(self._ticStepper._command_dict['gVariable'], self._ticStepper._variable_dict['operation_state'])
        except Exception as e:
            print("Error reading motor status")
            print(e)
            return False
        
        return miscResp, errResp, opResp
        
    # def homeForward(self):
    #     if self._fwdSwPresent:
    #         self.setRotationSpeed(_DEF_HOME_SPD_STEPS_PER_SEC)
    #         self._ticStepper.home('fwd')
    #     else:
    #         print('Forward limit switch not present. Homing (fwd) cannot be performed');

    # def homeReverse(self):
    #     if self._revSwPresent:
    #         self.setRotationSpeed(_DEF_HOME_SPD_STEPS_PER_SEC)
    #         self._ticStepper.home('rev')
    #     else:
    #         print('Reverse limit switch not present. Homing (rev) cannot be performed');

    def isLimitActive(self, limit):
        miscResp, _, _ = self.getMotorStatus()
        if limit == 'fwd':
            return bool(miscResp[0] & 2**_TIC_FWD_LIMIT_BIT)
        if limit == 'rev':
            return bool(miscResp[0] & 2**_TIC_REV_LIMIT_BIT)
    
    def isTargetValid(self, targetPos):
        if not self._isMotionRangeKnown:
            print('Motion range is not known. Cannot check target validity.')
            return False
        
        return (targetPos > self._allowedMotionRange[0]) and (targetPos < self._allowedMotionRange[1])

    def moveAbsSteps(self, positionSteps, waitForMotion = True, openLoopAssert = False):
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

    def moveRelSteps(self, steps, waitForMotion = True, openLoopAssert = False):
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

    def moveToIndexedPosition(self, index: 'Key to indexed position'): 
        if index in list(self._indexedPositions.keys()):
            self.moveAbsSteps(self._indexedPositions[index])

    def moveToLimit(self, limit: str, maxSteps=1E8, timeout_s = 60):
        # Inputs
        # limit: string, either 'fwd' or 'rev'
        # maxSteps: the maximum number of steps to take while searching for the limit switch
        # timeout_s: the maximum amount of time to spend looking for the limit switch
        
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
        
        print('Moving in ' + limit + ' direction until limit is encountered (manual homing) in 3 seconds...')
        sleep(3)
        
        self.setRotationSpeed(_DEF_HOME_SPD_STEPS_PER_SEC)
        elapsedTime = 0
        initialPosition = self._ticStepper.position('steps')
        currentPosition = initialPosition
        # Start moving, and poll the TicStepper limit switch during motion
        t1 = time()
        self._ticStepper.moveRelSteps(targetPos)
        print('Target pos = ' + str(targetPos))
        
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
            sleep(0.001)
            
        return True
            
    def print(self):
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

    def setIndexedPositions(self, positionMap: "dict() mapping keys to values (positions in steps)"):
        if type(positionMap) != dict:
            print('Please provide a dict() - returning.')
            return False

        if self._isMotionRangeKnown:
            vals = list(positionMap.values())
            for v in vals:
                if not self.isTargetValid(v):
                    print('One of the positions is out of motion range!')
                    return False

            self._indexedPositions.update(positionMap)

        else:
            # There is no known motion range
            self._indexedPositions.update(positionMap)         
        
    def setRotationSpeed(self, stepsPerSecond):
        try:
            self._ticStepper.rpm = 60*stepsPerSecond/self._ticStepper.steps_per_rev
        except Exception as e:
            print("Could not set TicStepper RPMs")
            print(e)
            
        self._stepsPerSecond = stepsPerSecond

    def _updateAllowedMotionRange(self):
        # Define range of allowed positions, including the soft limit buffer
        if self._isMotionRangeKnown:
            self._allowedMotionRange[0] = self._revLimSwPositionTic + _SOFTLIMIT_BUFFER_STEPS
            self._allowedMotionRange[1]  = self._fwdLimSwPositionTic - _SOFTLIMIT_BUFFER_STEPS

    def waitForMotion(self):
        print('In motion...')
        sleep(0.010)
        while self._ticStepper.isMoving():
            print('In motion....' + str(self._ticStepper.isMoving()))
            sleep(.005)

    def __del__(self):
        self.disable()
        del(self._ticStepper)
        return

# --------------------------------------------------------------------------------------------------


# ---------------------------------------PROPERTIES-------------------------------------------------
    @property 
    def indexedPositions(self) -> dict:
        return self._indexedPositions

   
# --------------------------------------------------------------------------------------------------


    

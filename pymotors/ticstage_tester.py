"""
Created on Tue Jul 30 08:22:07 2019
@author: paul.lebel
"""
from pymotors import TicStepper, TicStage
import numpy as np
import time
from time import sleep

_TIC_COM_MODE = 'serial'
_TIC_COM = '/dev/tty.usbserial-AD0JIXRE'
_TIC_BAUDRATE = 9600
_TIC_DEVICE_NUMBER = 14
_DEFAULT_NUM_IDX_POS = 8
def main():
  # myTicStepper = TicStepper(_TIC_COM_MODE, [_TIC_COM, _TIC_BAUDRATE], _TIC_DEVICE_NUMBER)
  # myStage = TicStage(myTicStepper, 500, 8)
  # myStage.enable()
  myStage = TicStage(_TIC_COM_MODE, [_TIC_COM, _TIC_BAUDRATE], _TIC_DEVICE_NUMBER, 500, 200, micro_step_factor=1, default_step_tol=1)
  myStage.enable = True
  myStage.discoverMotionRange()
  myStage.print()
  lims = myStage.getMotionRange()
  print(f"Lims: {lims[0]}, {lims[1]}")
  num_pos = 3
  values = np.round(np.linspace(lims[0], lims[1], num_pos))
  keys = range(num_pos)
  posDict = dict(zip(keys,values))
  myStage.setIndexedPositions(posDict)
  print(f"posDict: {posDict}")
  try:
    for pos in keys:
      print(f"Moving to index {pos} at position {posDict[pos]}")
      result = myStage.moveToIndexedPosition(pos, True)
      if result:
        print("Position reached")
      else:
        print("Position not reached!!!")
      time.sleep(1)
      print(f"TicStage position: {myStage.getCurrentPositionSteps()}")
      print(f"TicStepper position: {myStage.getCurrentPositionSteps()}")
  except Exception as exc:
    print(f"Exception occurred: {exc}")
  
  print("Testing moveAbsSteps in 3 seconds...")
  sleep(3)
  myStage.moveAbsSteps(190, step_tolerance=1)

  print("Testing moveRelSteps in 3 seconds...")
  sleep(3)
  myStage.moveRelSteps(-50, step_tolerance=1)
  myStage.print()

  # myStage.disable()
  # del(myStage)
if __name__ == "__main__":
  try: 
    main()
  except KeyboardInterrupt:
    pass
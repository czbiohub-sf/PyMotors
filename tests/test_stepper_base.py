import unittest
import warnings
import pymotors


class StepperBaseModified(pymotors.StepperBase):
    def __init__(self):
        super().__init__()
        self._fake_position_in_steps = 0

    def _position_in_steps(self):
        return self._fake_position_in_steps

    def _moveToTarget(self):
        while(self._fake_position_in_steps != self._target_steps):
            if self._fake_position_in_steps < self._target_steps:
                self._fake_position_in_steps += 1
            else:
                self._fake_position_in_steps -= 1


class Stepper_Utilities(unittest.TestCase):
    def setUp(self):
        # Warning generated from initialization : _microsteps not overloaded
        warnings.filterwarnings('ignore')
        self.stepper = StepperBaseModified()
        warnings.filterwarnings('error')

    def test_units_per_step(self):
        self.assertEqual(1, self.stepper.units_per_step)
        self.stepper.units_per_step = 10
        self.assertEqual(10, self.stepper.units_per_step)

    def test_steps_per_second_set_get(self):
        self.assertEqual(10, self.stepper.steps_per_second)
        self.stepper.steps_per_second = 100
        self.assertEqual(100, self.stepper.steps_per_second)
        try:
            warned = False
            self.stepper.steps_per_second = -1
        except UserWarning:
            warned = True
        self.assertEqual(True, warned)

    def test_units_per_second_set_get(self):
        self.assertEqual(10, self.stepper.units_per_second)
        self.stepper.units_per_second = 100
        self.assertEqual(100, self.stepper.units_per_second)
        try:
            warned = False
            self.stepper.units_per_second = -1
        except UserWarning:
            warned = True
        self.assertEqual(True, warned)

    def test_units_steps_conversion(self):
        self.stepper.units_per_second = 100
        self.assertEqual(100, self.stepper.steps_per_second)
        self.stepper.units_per_step = 10
        self.stepper.units_per_second = 100
        self.assertEqual(10, self.stepper.steps_per_second)

    def test_microsteps_set_get(self):
        warnings.filterwarnings('ignore',
                                "Overload _setMicrostep for functionality.")
        self.stepper.microsteps = 1 / 8
        microsteps = self.stepper.microsteps
        self.assertEqual(1 / 8, microsteps)
        try:
            warned = False
            self.stepper.microsteps = 1/10
        except UserWarning:
            warned = True
        self.assertEqual(True, warned)

    def test_position_steps_units(self):
        self.stepper.units_per_step = 10
        self.stepper._fake_position_in_steps = 10
        self.assertEqual(10, self.stepper.position('steps'))
        self.assertEqual(100, self.stepper.position('units'))

    def test_is_moving_and_stop(self):
        self.assertEqual(0, self.stepper.isMoving())
        self.stepper._fake_position_in_steps = 10
        self.stepper._target_steps = 15
        self.assertEqual(1, self.stepper.isMoving())
        self.stepper.stop()
        self.assertEqual(0, self.stepper.isMoving())

    def test_absolute_steps(self):
        self.stepper.enabled = True
        self.stepper.moveAbsSteps(100)
        self.assertEqual(100, self.stepper.position('steps'))
        self.stepper.moveAbsSteps(-100)
        self.assertEqual(-100, self.stepper.position('steps'))
        self.stepper.enabled = False
        try:
            warned = False
            self.stepper.moveAbsSteps(0)
        except UserWarning:
            warned = True
        self.assertEqual(True, warned)

    def test_absolute_units(self):
        self.stepper.enabled = True
        self.stepper.units_per_step = 10
        self.stepper.moveAbsUnits(100)
        self.assertEqual(10, self.stepper.position('steps'))
        self.stepper.moveAbsUnits(-100)
        self.assertEqual(-10, self.stepper.position('steps'))

    def test_relative_steps(self):
        self.stepper.enabled = True
        self.stepper.moveRelSteps(100)
        self.assertEqual(100, self.stepper.position('steps'))
        self.stepper.moveRelSteps(-200)
        self.assertEqual(-100, self.stepper.position('steps'))

    def test_relative_units(self):
        self.stepper.enabled = True
        self.stepper.units_per_step = 10
        self.stepper.moveRelUnits(100)
        self.assertEqual(100, self.stepper.position('units'))
        self.assertEqual(10, self.stepper.position('steps'))
        self.stepper.moveRelUnits(-100)
        self.assertEqual(0, self.stepper.position('units'))
        self.assertEqual(0, self.stepper.position('steps'))

    def test_move_units_rounding(self):
        self.stepper.enabled = True
        self.stepper.units_per_step = 10
        self.stepper.moveRelUnits(96)
        self.assertEqual(100, self.stepper.position('units'))
        self.assertEqual(10, self.stepper.position('steps'))
        self.stepper.moveRelUnits(-94)
        self.assertEqual(10, self.stepper.position('units'))
        self.assertEqual(1, self.stepper.position('steps'))
        self.stepper.moveAbsUnits(-6)
        self.assertEqual(-10, self.stepper.position('units'))
        self.assertEqual(-1, self.stepper.position('steps'))


if __name__ == '__main__':
    unittest.main()

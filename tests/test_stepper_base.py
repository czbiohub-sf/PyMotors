"""Unit tests for StepperBase."""
import unittest
import warnings
import pymotors
# pylint: disable=protected-access
# pylint: disable=missing-docstring


class StepperBaseModified(pymotors.StepperBase):
    """Modify StepperBase to keep track of position."""

    def __init__(self):
        super().__init__()
        self._fake_position_in_steps = 0

    def _position_in_steps(self):
        return self._fake_position_in_steps

    def _moveToTarget(self):
        while self._fake_position_in_steps != self._target_steps:
            if self._fake_position_in_steps < self._target_steps:
                self._fake_position_in_steps += 1
            else:
                self._fake_position_in_steps -= 1


class StepperBaseUtilities(unittest.TestCase):
    """Evaluate StepperBase methods and attributes."""

    def setUp(self):
        # Warning generated from initialization : _microsteps not overloaded
        warnings.filterwarnings('ignore')
        self.stepper = StepperBaseModified()
        warnings.filterwarnings('error')

    def test_dist_per_rev(self):
        self.assertEqual(1, self.stepper.dist_per_rev)
        self.stepper.dist_per_rev = 10
        self.assertEqual(10, self.stepper.dist_per_rev)

    def test_rpm_set_get(self):
        self.assertEqual(1, self.stepper.rpm)
        self.stepper.rpm = 100
        self.assertEqual(100, self.stepper.rpm)
        try:
            warned = False
            self.stepper.rpm = -1
        except UserWarning:
            warned = True
        self.assertEqual(True, warned)

    def test_dist_per_min_set_get(self):
        self.assertEqual(1, self.stepper.dist_per_min)
        self.stepper.rpm = 100
        self.assertEqual(100, self.stepper.dist_per_min)
        try:
            warned = False
            self.stepper.dist_per_min = -1
        except UserWarning:
            warned = True
        self.assertEqual(True, warned)

    def test_dist_steps_conversion(self):
        self.assertEqual(1, self.stepper._convStepsToDist(200))
        self.assertEqual(200, self.stepper._convDistToSteps(1))
        self.stepper.dist_per_rev = 10
        self.assertEqual(10, self.stepper._convStepsToDist(200))
        self.assertEqual(20, self.stepper._convDistToSteps(1))

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

    def test_microsteps_affect_dist_step_conversion(self):
        warnings.filterwarnings('ignore',
                                "Overload _setMicrostep for functionality.")
        self.assertEqual(1, self.stepper._convStepsToDist(200))
        self.assertEqual(200, self.stepper._convDistToSteps(1))
        self.stepper.microsteps = 1/2
        self.assertEqual(0.5, self.stepper._convStepsToDist(200))
        self.assertEqual(400, self.stepper._convDistToSteps(1))

    def test_position_in_steps_dist(self):
        self.stepper._fake_position_in_steps = 20
        self.assertEqual(20, self.stepper.position('steps'))
        self.assertEqual(.1, self.stepper.position('dist'))

    def test_is_moving_and_stop(self):
        self.stepper.enable = True
        self.assertEqual(0, self.stepper.isMoving())
        self.stepper._fake_position_in_steps = 10
        self.stepper._target_steps = 15
        self.assertEqual(1, self.stepper.isMoving())
        self.stepper.stop()
        self.assertEqual(0, self.stepper.isMoving())

    def test_absolute_steps(self):
        self.stepper.enable = True
        self.stepper.moveAbsSteps(100)
        self.assertEqual(100, self.stepper.position('steps'))
        self.stepper.moveAbsSteps(-100)
        self.assertEqual(-100, self.stepper.position('steps'))
        self.stepper.enable = False
        try:
            warned = False
            self.stepper.moveAbsSteps(0)
        except UserWarning:
            warned = True
        self.assertEqual(True, warned)

    def test_absolute_dist(self):
        self.stepper.enable = True
        self.stepper.dist_per_rev = 10
        self.stepper.moveAbsDist(10)
        self.assertEqual(200, self.stepper.position('steps'))
        self.stepper.moveAbsDist(-10)
        self.assertEqual(-200, self.stepper.position('steps'))

    def test_relative_steps(self):
        self.stepper.enable = True
        self.stepper.moveRelSteps(100)
        self.assertEqual(100, self.stepper.position('steps'))
        self.stepper.moveRelSteps(-200)
        self.assertEqual(-100, self.stepper.position('steps'))

    def test_relative_units(self):
        self.stepper.enable = True
        self.stepper.dist_per_rev = 10
        self.stepper.moveRelDist(10)
        self.assertEqual(10, self.stepper.position('dist'))
        self.assertEqual(200, self.stepper.position('steps'))
        self.stepper.moveRelDist(-20)
        self.assertEqual(-10, self.stepper.position('dist'))
        self.assertEqual(-200, self.stepper.position('steps'))

    def test_move_units_rounding(self):
        self.stepper.enable = True
        self.stepper.dist_per_rev = 200
        self.stepper.moveRelDist(200.3)
        self.assertEqual(200, self.stepper.position('dist'))
        self.assertEqual(200, self.stepper.position('steps'))
        self.stepper.moveRelDist(-199.6)
        self.assertEqual(0, self.stepper.position('dist'))
        self.assertEqual(0, self.stepper.position('steps'))
        self.stepper.moveAbsDist(-6.3)
        self.assertEqual(-6, self.stepper.position('dist'))
        self.assertEqual(-6, self.stepper.position('steps'))


if __name__ == '__main__':
    unittest.main()

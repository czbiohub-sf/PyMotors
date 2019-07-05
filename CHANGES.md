# Relase notes

All notable changes to this project will be documented in this file. This module adheres to [Semantic Versioning](https://semver.org/).

## 1.0.1
- Minor corrections to StepperBase and TicStepper documentation.

## 1.0.0
- Replace steps_per_second with rpm
- Replace units_per_second with dist_per_min
- Account for microsteps in step <-> dist conversion
- Make speed independent of microsteps setting
- Remove accel/decel methods from StepperBase and move to TicStepper
- Add additional documentation
- Create hardware testing script for evaluating method behavior on RPi

## 0.1.0
- Add accel/decel method to StepperBase with tests
- Add _setAccel and _setDecel methods to TicStepper with tests
- Fix StepperBase method `stop`
- Debug and validate TicStepper I2C communication
- Debug and validate TicStepper serial communication
- Rename StepperBase method `enabled` to `enable`
- Corrected credit to Tic board vendor, Pololu

## 0.0.1
- Add support for stepper motors
- Add support for DC motors
- Add support for Pololu Tic stepper driver, T500
- Add I2C communication protocol for TicStepper
- Add serial communication protocol for TicStepper
- Add Makefile options for testing:
  - Steppers
  - DC motors
  - Tic board and communication interfaces
  - Base classes
- Add installation and testing recommendations

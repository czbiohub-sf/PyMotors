# Relase notes

All notable changes to this project will be documented in this file. This module adheres to [Semantic Versioning](https://semver.org/).
## 0.0.2
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

# PyMotors

## Introduction
This repository contains Python classes and/or functions that have been designed for various motor control applications in the CZ Biohub Bioengineering team. All utilities support Python 3.7+.

## Contents
* __StepperBase__ - A generalized base class for stepper motors.
* __TicStepper__ - An implementation specific stepper motor class based off of the T500 stepper driver.
* __DcBase__ - A generalized base class for DC motors.
* __LimitedDc__ - A class that provides control over DC motor with external limits.

## Dependencies

TicStepper :: smbus2 (I2C communication)<br>
TicStepper :: pyserial (Serial communication)<br>

## Installation and Use
### Installing Module
1. Create and/or activate a virtual environment in a convenient location with Python3
2. Download / clone this repository
3. Navigate to the base of the repository
4. Install setuptools (__pip install setuptools__)
5. Test the module for completeness (__python setup.py test__)
6. Install module (__pip install .__)

### Updating Module from Repository
1. Pull changes from remote repository
2. Activate virtual environment with previous install
3. Test the module for completeness (__python setup.py test__)
3. Update module (__pip install . --upgrade__)

### Using Module
1. Edit files to include `import pymotors` or a variant such as `from pymotors import TicStepper`
2. Activate virtual environment with module installed
3. Execute python script or application


## How to Contribute
If you would like to contribute to PyMotors, please review the guidelines described in [CONTRIBUTING.md](https://github.com/czbiohub/PyMotors/blob/master/CONTRIBUTING.md).

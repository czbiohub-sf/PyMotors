"""Evaluate Tic stepper driver with a Raspberry Pi."""
from time import sleep
import pymotors


def eval_tic(tic):
    """Short testing script to confirm functionality.

    Note: Ending position will not equal starting position due to converting
    from full steps to microsteps when not at position 0. Also, to help with
    visualizing motor movement, tape the end of the rotor.

    """
    print('WARNING! MOTOR ROTOR MUST BE DECOUPLED FROM SYSTEM BEFORE TESTING')
    sleep(2)
    print('Press `CTL-C` to abort.')
    print('Beginning in:')
    print('3')
    sleep(1)
    print('2')
    sleep(1)
    print('1')
    sleep(1)

    print('Enabling motor.')
    sleep(1)
    tic.enable = True
    tic.microsteps = 1

    print('Moving clockwise at default speed for 50 steps.')
    sleep(1)
    tic.moveAbsSteps(50)
    wait_for_motor(tic)

    print('Changing velocity to 10 RPM + moving 250 steps counter clockwise.')
    sleep(1)
    tic.rpm = 10
    tic.moveRelSteps(-250)
    wait_for_motor(tic)

    print('Changing microsteps to 1/8 + moving 800 steps clockwise.')
    print('NOTE: RPM should not change when using microsteps.')
    sleep(1)
    tic.microsteps = 1/8
    tic.moveRelSteps(800)
    wait_for_motor(tic)

    print('Updating accel/decel + moving to position 0.')
    sleep(1)
    tic.accel_decel = [0x00700000, 0x00700000]
    tic.moveAbsDist(0)
    wait_for_motor(tic)

    print('Moving 20 revolutions clockwise at max recommended speed.')
    sleep(1)
    tic.dist_per_min = 200
    tic.moveRelDist(20)
    wait_for_motor(tic)

    print('Moving to position 0 + evaluating stop command')
    tic.moveAbsDist(0)
    sleep(2)
    tic.stop()
    wait_for_motor(tic)

    print('Resuming movement to position 0')
    tic.moveAbsDist(0)
    wait_for_motor(tic)

    print('De-energizing.')
    tic.enable = False


def wait_for_motor(motor):
    """Wait for motor to finish moving."""
    moving = 1
    while moving:
        sleep(0.2)
        try:
            moving = motor.isMoving()
        except OSError:
            moving = 1


if __name__ == '__main__':
    TIC = pymotors.TicStepper('I2C', 1, 14)
    eval_tic(TIC)

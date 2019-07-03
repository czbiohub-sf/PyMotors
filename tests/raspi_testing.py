from time import sleep
import pymotors


def eval_tic(tic: pymotors.TicStepper):
    """Short testing script to confirm functionality."""
    print('Tape on the motor shaft will help visualize motion.')
    print('Motor will begin moving shortly. Press `CTL-C` to abort.')
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

    print('Moving clockwise at default speed for 100 steps.')
    sleep(1)
    tic.moveAbsSteps(100)
    wait_for_motor(tic)

    print('Changing velocity to 10 RPM + moving 200 steps counter clockwise.')
    sleep(1)
    tic.rpm = 10
    tic.moveRelSteps(-200)
    wait_for_motor(tic)

    print('Changing microsteps to 1/8 + moving 200 steps clockwise.')
    print('NOTE: Speed should not change when using microsteps.')
    sleep(1)
    tic.microsteps = 1/8
    tic.moveRelSteps(200)
    wait_for_motor(tic)

    print('Updating accel/decel + moving to position 0.')
    print('NOTE: Movement confirms that microstepping is behaving properly.')
    sleep(1)
    tic.accel_decel = tic.accel_decel * 8
    tic.moveAbsDist(0)
    wait_for_motor(tic)

    print('Moving 10 revolutions clockwise at max recommended speed.')
    sleep(1)
    tic.dist_per_min = 200
    tic.moveRelDist(10)
    wait_for_motor(tic)

    print('Moving to position 0 + evaluating stop command')
    tic.moveAbsDist(0)
    sleep(1)
    tic.stop()
    wait_for_motor(tic)

    print('Resuming movement to position 0')
    tic.moveAbsDist(0)
    wait_for_motor(tic)

    print('De-energizing.')
    tic.enable = False


def wait_for_motor(motor):
    """Wait for motor to finish moving."""
    while motor.isMoving():
        pass


if __name__ == '__main__':
    TIC = pymotors.TicStepper('I2C', '/dev/i2c-0', 14)
    eval_tic(TIC)

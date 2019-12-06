import RPi.GPIO as GPIO
from gpiozero import MCP3008
from time import sleep

# Confirm that motor can be controlled by custom control board
en1 = 22
en2 = 23
rev = 24
fwd = 25
adc_chan = 7
adc_port = 0
pwm_freq = 100000
pwm_duty = 50

GPIO.setmode(GPIO.BCM)
GPIO.setup(en1, GPIO.OUT)
GPIO.setup(en2, GPIO.OUT)
GPIO.setup(rev, GPIO.OUT)
GPIO.setup(fwd, GPIO.OUT)

GPIO.output(en2, GPIO.LOW)

# Spin reverse
GPIO.output(en1, GPIO.HIGH)
GPIO.output(rev, GPIO.HIGH)
sleep(1)
GPIO.output(rev, GPIO.LOW)

# Spin forward
sleep(0.5)
GPIO.output(fwd, GPIO.HIGH)
sleep(1)
GPIO.output(fwd, GPIO.LOW)

# Test PWM
pwm_rev = GPIO.PWM(rev, pwm_duty)
pwm_fwd = GPIO.PWM(fwd, pwm_duty)

pwm_rev.start(pwm_duty)
sleep(1)
pwm_rev.stop()

pwm_fwd.start(pwm_duty)
sleep(1)
pwm_fwd.stop()

GPIO.output(en1, GPIO.LOW)

# Test Motor 2
pwm_rev.start(pwm_duty)
GPIO.output(en2, GPIO.HIGH)
sleep(1)
pwm_rev.stop()

pwm_fwd.start(pwm_duty)
sleep(1)
pwm_fwd.stop()

GPIO.output(en2, GPIO.LOW)

## Test ADC
adc = MCP3008(channel=adc_chan)
print(adc.value)
sleep(.2)
print(adc.value)
sleep(.2)
print(adc.value)
sleep(.2)
print(adc.value)
sleep(.2)
print(adc.value)

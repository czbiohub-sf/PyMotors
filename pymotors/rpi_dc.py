"""Implementation specific class for controlling a DC motor via RPi.GPIO."""
from .dc_base import DcBase
import RPi.GPIO as GPIO


class RPiDc(DcBase):
    """Control a DC motor with a Raspberry Pi."""

    def __init__(self, fwd_pin=[], rev_pin=[]):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(fwd_pin, GPIO.OUT)
        GPIO.setup(rev_pin, GPIO.OUT)
        GPIO.output([fwd_pin, rev_pin], GPIO.LOW)
        super().__init__(fwd_pin, rev_pin)

    def _togglePins(self, set_dir: str):
        pins = self._toggle_dict[set_dir]
        GPIO.output(pins[1], GPIO.LOW)
        GPIO.output(pins[0], GPIO.HIGH)

import threading
import warnings


class DcBase():
    def __init__(self, forward_pins=[], reverse_pins=[]):
        self._toggle_dict = {'fwd': [forward_pins, reverse_pins],
                             'rev': [reverse_pins, forward_pins],
                             'stop': [[], forward_pins + reverse_pins],
                             }
        self._timer = threading.Timer(0, self.stop)
        self.stop()

    def __del__(self):
        self._clearExpiration()

    def moveFwd(self, seconds=0):
        self.direction = 'fwd'
        self.is_moving = True
        self._move(seconds)

    def moveRev(self, seconds=0):
        self.direction = 'rev'
        self.is_moving = True
        self._move(seconds)

    def stop(self):
        self.direction = 'stop'
        self.is_moving = False
        self._clearExpiration()
        self._move()

    def _move(self, seconds: float = 0):

        if (
            self.direction != 'fwd'
            and self.direction != 'rev'
            and self.direction != 'stop'
           ):
            warnings.warn('Direction {} not recgonized'.format(dir))
            return

        pass_fail = self._togglePins(self._toggle_dict[self.direction])
        if pass_fail == 1:
            self._setExpiration(seconds)

    def _togglePins(self, dir: str):
        raise NotImplementedError('_togglePins has not been overridden.')

    def _setExpiration(self, seconds: int):
        if seconds > 0:
            self._timer = threading.Timer(seconds, self.stop)
            self._timer.start()

    def _clearExpiration(self):
        self._timer.cancel()


class LimitedDc(DcBase):

    def __init__(self, dir_limit: dict, forward_pins=[], reverse_pins=[]):
        self._limits = {
                        'rev': None,
                        'fwd': None,
                        'stop': None,
                        }
        for entry in dir_limit:
            self._limits[entry] = dir_limit[entry]
        self._timer_limits = threading.Timer(1, self._checkLimits)
        self._timer_limits.start()
        super(LimitedDc, self).__init__()

    def _checkLimits(self, direction):
        adc_limit = self._limits[direction]
        if adc_limit is not None:
            if self._pollLimits(self.direction) >= adc_limit:
                self.stop()
                return 'Limit reached'
            else:
                self._timer_limits = threading.Timer(.1, self._checkLimits)
                self._timer_limits.start()
        return 'OK'

    def _clearExpiration(self):
        if self._timer_limits.is_alive():
            self._timer_limits.cancel()
            self._timer_limits.join()
        if self._timer.is_alive():
            self._timer.cancel()
            self._timer.join()

    def _pollLimits(self, direction):
        raise NotImplementedError('_pollLimits has not been overridden.')

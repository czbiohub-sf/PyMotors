import threading
import warnings


class DcBase():
    def __init__(self):
        self._timer = threading.Timer(0, self.stop)
        self.stop()

    def moveFwd(self, seconds=0):
        self._move('fwd', seconds)

    def moveRev(self, seconds=0):
        self._move('rev', seconds)

    def stop(self):
        self._clearExpiration()
        self._move('stop')

    def _move(self, dir: str, seconds: float = 0):
        self.direction = dir
        self._togglePins(dir)
        self._setExpiration(seconds)
        if dir == 'stop':
            self.is_moving = False
        elif dir == 'fwd' or dir == 'rev':
            self.is_moving = True
        else:
            warnings.warn('Direction {} not recgonized'.format(dir))

    def _togglePins(self, dir: str):
        raise NotImplementedError('_togglePins has not been overridden.')

    def _setExpiration(self, seconds: int):
        if seconds > 0:
            self._timer = threading.Timer(seconds, self.stop)
            self._timer.start()

    def _clearExpiration(self):
        self._timer.cancel()


class LimitedDc(DcBase):

    def __init__(self, dir_limit: dict):
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

    def _checkLimits(self):
        if self.direction != 'stop':
            if self._pollLimits(self.direction) >= self._limits[self.direction]:
                self.stop()
            else:
                self._timer_limits = threading.Timer(.1, self._checkLimits)
                self._timer_limits.start()

    def _clearExpiration(self):
        if self._timer_limits.is_alive():
            self._timer_limits.cancel()
            self._timer_limits.join()
        if self._timer.is_alive():
            self._timer.cancel()
            self._timer.join()

    def _pollLimits(self, direction):
        raise NotImplementedError('_pollLimits has not been overridden.')

import threading


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
        self.is_moving = False

    def _move(self, dir: str, seconds: int):
        self.direction = dir
        self._togglePins(dir)
        self._setExpiration(seconds)
        self.is_moving = True

    def _togglePins(self, dir: str):
        raise NotImplementedError('_togglePins has not been overridden.')

    def _setExpiration(self, seconds: int):
        if seconds > 0:
            self._timer = threading.Timer(seconds, self.stop).start()

    def _clearExpiration(self):
        self.timer.cancel()


class LimitedDc(DcBase):

    def __init__(self, dir_limit: list):
        super(LimitedDc, self).__init__()
        self._limits = {
                        'rev': None,
                        'fwd': None,
                        'stop': None,
                        }
        for entry in dir_limit:
            self._limits[entry[0]] = entry[1]
        self._timer_limits = threading.Timer(0, self._checkLimits)

    def _checkLimits(self):
        if self.direction is not None:
            if self._pollLimits() >= self._limits[self.direction]:
                self.stop()
            else:
                self._timer_limits = \
                 threading.Timer(.1, self._checkLimits).start()

    def _clearExpiration(self):
        self._timer_limits.cancel()
        self.timer.cancel()

    def _pollLimits(self):
        raise NotImplementedError('_pollLimits has not been overridden.')

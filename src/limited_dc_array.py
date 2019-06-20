from dc_base import LimitedDc
from gpiozero import MCP3008
from gpiozero import LED as Pin



class LimitedDc(DcBase):

    def __init__(self, pin_list: list, dir_limit: list):
        self._fwd_pin = pin_list[0]
        self._rev_pin = pin_list[1]
        self._limit_channel = pin_list[2]
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
        return MCP3008(self._limit_channel).value

    def _togglePins(self, dir: str):
        if dir == 'stop'

class LimitedDcArray(LimitedDc):
    def __init__(self, pin_array: list, dir_limit: list):
        for motor in pin_array[0]:
            self.dc[motor] = LimitedDc(dir_limit[motor])
            self.dc[motor]._fwd_pin = pin_array[motor][0]
            self.dc[motor]._rev_pin = pin_array[motor][1]
            self.dc[motor]._limit_pin = pin_array[motor][2]
            self.dc[motor]._pollLimits = self._pollLimits
            self.dc[motor]._togglePins = self._togglePins

    def _pollLimits(self):

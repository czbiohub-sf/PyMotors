from dc_base import LimitedDc


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

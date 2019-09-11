import logging
from logging import NullHandler

LOG = logging.getLogger(__name__).addHandler(NullHandler())

# pylint: disable = invalid-name


class DcBase():
    def __init__(self, forward_pins=[], reverse_pins=[]):
        self._toggle_dict = {'fwd': [forward_pins, reverse_pins],
                             'rev': [reverse_pins, forward_pins],
                             'stop': [[], forward_pins + reverse_pins],
                             }
        self.is_moving = False
        self.direction = 'stop'
        LOG.debug('DC object created.')

    def __del__(self):
        self.stop()
        LOG.debug('DC object deleted.')

    def moveFwd(self):
        """Drive motor forward and update attributes."""
        set_dir = 'fwd'
        pass_fail = self._move(set_dir)
        if pass_fail:
            self.is_moving = True
            self.direction = set_dir
            LOG.debug('DC motor moving forward.')

    def moveRev(self):
        """Drive motor in reverse and update attributes."""
        set_dir = 'rev'
        pass_fail = self._move(set_dir)
        if pass_fail:
            self.is_moving = True
            self.direction = set_dir
            LOG.debug('DC motor moving reverse.')

    def stop(self):
        """Stop the motor and update attributes."""
        set_dir = 'stop'
        pass_fail = self._move(set_dir)
        if pass_fail:
            self.is_moving = False
            self.direction = set_dir
            LOG.debug('DC motor stopped.')

    def _move(self, set_dir: str):
        pass_fail = False
        if set_dir not in self._toggle_dict:
            LOG.warning('Direction `%s` not recgonized.' % set_dir)
            return pass_fail

        pass_fail = self._togglePins(self._toggle_dict[set_dir])
        return pass_fail

    def _togglePins(self, set_dir: str):
        raise NotImplementedError('_togglePins has not been overridden.')


class LimitedDc(DcBase):

    def __init__(self, dir_limit: dict, fwd_pin=[], rev_pin=[]):
        self._limits = {
                        'rev': None,
                        'fwd': None,
                        'stop': None,
                        }
        for entry in dir_limit:
            self._limits[entry] = dir_limit[entry]
        self._timer_limits = threading.Timer(1, self._checkLimits)
        self._timer_limits.start()
        super(LimitedDc, self).__init__(fwd_pin, rev_pin)

    def _checkLimits(self):
        adc_limit = self._limits[self.direction]
        if adc_limit is not None:
            if self._pollLimits() >= adc_limit:
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

    def _pollLimits(self):
        raise NotImplementedError('_pollLimits has not been overridden.')

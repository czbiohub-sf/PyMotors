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
    """
    DC motor with limit setting and limit polling functionality.
    """

    def __init__(self, fwd_pins=[], rev_pins=[]):
        self._limits = {}
        super(LimitedDc, self).__init__(fwd_pins, rev_pins)

    def setDirLimit(self, set_dir: str, limit: float):
        """Set a threshold value for a specified direction."""
        if set_dir == 'fwd' or 'rev':
            self._limits[set_dir] = limit
            LOG.debug('Motor limit set. Direction: `%s` | Threshold: %f' %
                      (set_dir, limit))
        else:
            LOG.warning('Direction `%s` not recognized.' % set_dir)

    def _checkLimits(self):
        """Stop motor if threshold exceeded."""
        if self.direction in self._limits:
            adc_limit = self._limits[self.direction]
            obs = self._pollLimits()
            if obs >= adc_limit:
                self.stop()
                LOG.debug('Motor limit reached. Threshold: %f | Observed: %f' %
                          (adc_limit, obs))

    def _pollLimits(self):
        raise NotImplementedError('_pollLimits has not been overridden.')

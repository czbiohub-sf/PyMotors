import logging
from logging import NullHandler

LOG = logging.getLogger(__name__)
LOG.addHandler(NullHandler())
# pylint: disable = invalid-name


class DcArray():
    """Provides control over an array of DC motor objects."""

    def __init__(self, dc_motors: list):
        self.dc = []
        i = 0
        for motor in dc_motors:
            LOG.debug('Instantiating DC motor %d.', i)
            self.dc.append(dc_motors[motor])
            i = i + 1

    def __del__(self):
        self.stop()
        self._deactivate()
        LOG.debug('DC array deleted.')

    def moveFwd(self, motors: list = None):
        """All or specified motors will be driven forward."""
        self._activateFwd()
        if motors is None:
            motors = range(len(self.dc))
        for motor in motors:
            LOG.debug('Driving DC motor %d forward.', motor)
            self.dc[motor].moveFwd()

    def moveRev(self, motors: list = None):
        """All or specified motors will be driven reverse."""
        self._activateRev()
        if motors is None:
            motors = range(len(self.dc))
        for motor in motors:
            LOG.debug('Driving DC motor %d reverse.', motor)
            self.dc[motor].moveRev()

    def stop(self, motors: list = None):
        """All motors will be stopped."""
        if motors is None:
            motors = range(len(self.dc))
        for motor in motors:
            LOG.debug('Stopping DC motor %d', motor)
            self.dc[motor].stop()

    def setSpeed(self, value):
        """Change speed of all DC motors."""
        raise NotImplementedError('Method has not been overridden.')

    @staticmethod
    def _activateFwd():
        pass

    @staticmethod
    def _activateRev():
        pass

    @staticmethod
    def _deactivate():
        pass

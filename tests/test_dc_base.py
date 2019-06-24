import unittest
from unittest.mock import patch
import warnings
import src


class DcBase_Utilities(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings('error')
        self.patchToggle = patch('src.DcBase._togglePins')
        self.patchToggle.start()
        self.dc = src.DcBase()

    def tearDown(self):
        self.dc._clearExpiration()
        self.patchToggle.stop()

    def test_toggle_pins(self):
        self.dc._togglePins('fake')
        self.dc._togglePins.assert_called_with('fake')
        self.patchToggle.stop()
        try:
            warned = False
            self.dc._togglePins('fake')
        except NotImplementedError:
            warned = True
        self.assertEqual(True, warned)
        self.patchToggle.start()

    @patch('src.dc_base.threading')
    def test_set_and_clear_unexpired_timer(self, MockThreads):
        self.dc._setExpiration(1)
        MockThreads.Timer.assert_called_with(1, self.dc.stop)
        self.dc._timer.start.assert_called_with()
        self.dc._clearExpiration()
        self.dc._timer.cancel.assert_called_with()

    def test_clear_standby_timer(self):
        self.dc._clearExpiration()

    def test_move_wrong_format(self):
        self.dc._move('fwd')
        self.dc._move('rev')
        self.dc._move('stop')
        try:
            warned = 0
            self.dc._move('fake', 1)
        except UserWarning:
            warned = 1
        self.assertEqual(True, warned)

    def test_move_fwd(self):
        self.assertEqual(False, self.dc.is_moving)
        self.dc.moveFwd()
        self.assertEqual(True, self.dc.is_moving)

    def test_move_rev(self):
        self.dc.moveRev()
        self.assertEqual(True, self.dc.is_moving)

    def test_stop(self):
        self.dc.moveRev(1)
        self.dc.stop()
        self.assertEqual(False, self.dc.is_moving)


class LimitedDc_Utilities(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings('error')
        self.limits_dict = {'fwd': 1, 'rev': 0.5, }
        self.patchPoll = patch('src.LimitedDc._pollLimits')
        self.patchPoll.start()
        self.patchToggle = patch('src.LimitedDc._togglePins')
        self.patchToggle.start()
        self.dc = src.LimitedDc(self.limits_dict)

    def tearDown(self):
        self.dc._clearExpiration()

    def test_limit_dict(self):
        self.assertEqual(self.limits_dict['fwd'], self.dc._limits['fwd'])
        self.assertEqual(self.limits_dict['rev'], self.dc._limits['rev'])
        self.assertEqual(None, self.dc._limits['stop'])

    def test_poll_limits(self):
        self.dc._pollLimits('fwd')
        self.dc._pollLimits.assert_called_with('fwd')

    def test_check_limits(self):
        self.dc._pollLimits = unittest.mock.Mock(return_value=0.1)
        self.dc.stop()
        self.dc._checkLimits()
        self.dc.moveRev()
        self.dc._checkLimits()
        self.assertEqual(True, self.dc._timer_limits.is_alive())
        self.dc._pollLimits = unittest.mock.Mock(return_value=self.limits_dict['rev'])
        self.dc._checkLimits()
        self.assertEqual(False, self.dc._timer_limits.is_alive())
        self.dc.moveFwd(2)
        self.dc._checkLimits()
        self.assertEqual(True, self.dc._timer_limits.is_alive())
        self.assertEqual(True, self.dc._timer.is_alive())
        self.dc._pollLimits = unittest.mock.Mock(return_value=self.limits_dict['fwd'])
        self.dc._checkLimits()
        self.assertEqual(False, self.dc._timer_limits.is_alive())
        self.assertEqual(False, self.dc._timer.is_alive())

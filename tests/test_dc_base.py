import unittest
from unittest.mock import patch
import warnings
import pymotors


class DcBase_Utilities(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings('error')
        pymotors.DcBase._togglePins = lambda self, direction: True
        self.fwd_pin = [1]
        self.rev_pin = [2]
        self.dc = pymotors.DcBase(self.fwd_pin, self.rev_pin)

    def test_toggle_dict(self):
        tog_dict = self.dc._toggle_dict
        self.assertEqual([self.fwd_pin, self.rev_pin], tog_dict['fwd'])
        self.assertEqual([self.rev_pin, self.fwd_pin], tog_dict['rev'])
        self.assertEqual([[], self.fwd_pin + self.rev_pin], tog_dict['stop'])

    def test_move_wrong_format(self):
        self.dc.direction = 'fwd'
        self.dc._move(self.dc.direction)
        self.dc.direction = 'rev'
        self.dc._move(self.dc.direction)
        self.dc.direction = 'stop'
        pass_fail = self.dc._move(self.dc.direction)
        self.assertEqual(True, pass_fail)
        self.dc.direction = 'fake'
        pass_fail = self.dc._move(self.dc.direction)
        self.assertEqual(False, pass_fail)

    def test_move_fwd(self):
        self.assertEqual(False, self.dc.is_moving)
        self.dc.moveFwd()
        self.assertEqual(True, self.dc.is_moving)

    def test_move_rev(self):
        self.dc.moveRev()
        self.assertEqual(True, self.dc.is_moving)

    def test_stop(self):
        self.dc.moveRev()
        self.dc.stop()
        self.assertEqual(False, self.dc.is_moving)


class LimitedDc_Utilities(unittest.TestCase):
    def setUp(self):
        warnings.filterwarnings('error')
        pymotors.LimitedDc._togglePins = lambda self, direction: True
        self.fwd_pin = [1]
        self.rev_pin = [2]
        self.dc = pymotors.LimitedDc(self.fwd_pin, self.rev_pin)

    def test_set_limits(self):
        limits_dict = {'fwd': 1, 'rev': 0.5, }
        self.dc.setDirLimit('fwd', limits_dict['fwd'])
        self.assertEqual(limits_dict['fwd'], self.dc._limits['fwd'])
        self.dc.setDirLimit('rev', limits_dict['rev'])
        self.assertEqual(limits_dict['rev'], self.dc._limits['rev'])

    def test_toggle_dict(self):
        tog_dict = self.dc._toggle_dict
        self.assertEqual([self.fwd_pin, self.rev_pin], tog_dict['fwd'])
        self.assertEqual([self.rev_pin, self.fwd_pin], tog_dict['rev'])
        self.assertEqual([[], self.fwd_pin + self.rev_pin], tog_dict['stop'])

    def test_check_limits(self):
        self.dc._pollLimits = lambda : 0.1
        self.dc.setDirLimit('fwd', 1)
        self.dc.moveFwd()
        self.dc.checkLimits()
        self.assertEqual('fwd', self.dc.direction)
        self.dc.setDirLimit('fwd', 0)
        self.dc.checkLimits()
        self.assertEqual('stop', self.dc.direction)

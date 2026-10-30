import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from engine import assess, market_alert
from refresh_announcements import classify, normalize


class FinancialRulesTest(unittest.TestCase):
    def setUp(self):
        self.promise = dict(metric='revenue_growth',period='FY2025',period_end='2025-03-31',unit='percent',basis='constant_currency',scope='consolidated',low=4.5,high=5)
        self.outcome = {k:self.promise[k] for k in ('metric','period','unit','basis','scope')}
        self.outcome.update(value=4.2,published_at='2025-04-17')

    def test_missed_latest_range_exact_delta(self):
        result=assess(self.promise,self.outcome,'2026-10-30')
        self.assertEqual((result['status'],result['delta_pp']),('missed',-0.3))

    def test_earlier_revision_can_be_met(self):
        self.promise.update(low=3.75,high=4.5)
        self.assertEqual(assess(self.promise,self.outcome,'2026-10-30')['status'],'met')

    def test_exceeded_is_separate_from_met(self):
        self.promise.update(low=3,high=4)
        self.assertEqual(assess(self.promise,self.outcome,'2026-10-30')['status'],'exceeded')

    def test_each_comparability_dimension_blocks_verdict(self):
        for key in ('metric','period','unit','basis','scope'):
            with self.subTest(key=key):
                wrong=copy.deepcopy(self.outcome)
                wrong[key]='mismatched'
                self.assertEqual(assess(self.promise,wrong,'2026-10-30')['status'],'not_comparable')

    def test_future_year_is_pending_even_if_value_is_present(self):
        self.assertEqual(assess(self.promise,self.outcome,'2025-01-16')['status'],'pending')

    def test_future_publication_does_not_leak_into_past(self):
        self.assertEqual(assess(self.promise,self.outcome,'2025-04-01')['status'],'insufficient_evidence')

    def test_missing_outcome_is_not_a_miss(self):
        self.assertEqual(assess(self.promise,None,'2026-10-30')['status'],'insufficient_evidence')

    def test_volume_baseline_excludes_current_session(self):
        result=market_alert([100]*20+[104],[100]*20+[300])
        self.assertEqual(result['volume_multiple'],3)
        self.assertTrue(result['volume_triggered'])
        self.assertTrue(result['price_triggered'])

    def test_threshold_change_changes_alert(self):
        result=market_alert([100]*20+[104],[100]*20+[300],price_threshold=5,volume_threshold=4)
        self.assertFalse(result['price_triggered'])
        self.assertFalse(result['volume_triggered'])

    def test_insufficient_volume_history_is_not_no_alert(self):
        self.assertEqual(market_alert([100],[1])['status'],'insufficient_history')

    def test_unknown_announcement_is_not_assumed_routine(self):
        self.assertEqual(classify('Unrecognized disclosure'),('unclassified',30))

    def test_bad_announcement_date_is_not_today(self):
        self.assertIsNone(normalize({'symbol':'INFY','an_dt':'invalid'}, {'INFY'}))


if __name__=='__main__':
    unittest.main()

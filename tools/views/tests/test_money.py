"""The ledger, authorities, standing and the outward refusal (METHOD.md section 7b)."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))  # so these run from tests/, tools/views or the repo root
import copy, unittest

from tests.helpers import checks, seed_record

FULL3 = seed_record('FULL3')


def run(rec, mode='record', strict=True):
    _rec, R = checks.check_record(copy.deepcopy(rec), mode, strict)
    return R


def text(R):
    return ' '.join(R.errors + R.warnings)


class Money(unittest.TestCase):
    def test_example_is_clean(self):
        R = run(FULL3)
        self.assertTrue(R.ok, text(R))

    def test_sum_is_computed(self):
        rec = copy.deepcopy(FULL3)
        by = {f['id']: f for f in rec['facts']}
        res = checks.make_resolver(by, {}, {}, {e['id']: e for e in rec['exhibits']}, rec['ledger'], {a['id']: a for a in rec['authorities']})
        self.assertEqual(checks.expand('{sum}', res), '$39,500.00')
        self.assertEqual(checks.expand('{sum:after:A1}', res), '$31,500.00')
        self.assertEqual(checks.expand('{sum:within:A1}', res), '$8,000.00')
        self.assertEqual(checks.expand('{sum:to:p3}', res), '$4,000.00')

    def test_amount_not_in_document_fails(self):
        rec = copy.deepcopy(FULL3)
        rec['ledger'][3]['amount'] = '15,500.00'
        self.assertIn('L4', text(run(rec)))

    def test_typed_total_fails(self):
        rec = copy.deepcopy(FULL3)
        rec['meta']['summary'] = 'The statements show $39,500.00 in transactions.'
        self.assertFalse(run(rec).ok)

    def test_bad_filter_and_empty_selection_fail(self):
        for ph in ('{sum:after:A9}', '{sum:colour:red}', '{sum:to}', '{sum:to:nobody}'):
            rec = copy.deepcopy(FULL3)
            rec['meta']['summary'] = 'Total: ' + ph + '.'
            self.assertFalse(run(rec).ok, ph)

    def test_authority_must_end_at_a_fact(self):
        rec = copy.deepcopy(FULL3)
        rec['authorities'][0]['to'] = 'F99'
        self.assertIn('not a fact', text(run(rec)))

    def test_characterization_fails(self):
        rec = copy.deepcopy(FULL3)
        rec['ledger'][0]['note'] = 'The thief moved this.'
        self.assertFalse(run(rec).ok)

    def test_no_standing_is_noted(self):
        rec = copy.deepcopy(FULL3)
        del rec['meta']['standing']
        self.assertIn('whose claim', text(run(rec, strict=False)))

    def test_outward_refused(self):
        R = run(FULL3, 'outward')
        self.assertIn('outward: false', text(R))
        self.assertFalse(R.ok)

    def test_position_by_date(self):
        by = {f['id']: f for f in FULL3['facts']}
        a = FULL3['authorities'][0]
        self.assertEqual(checks.entry_position({'date': '2025-06-18'}, a, by), 'on the end date')
        self.assertEqual(checks.entry_position({'date': '2025-03-03'}, a, by), 'before')


if __name__ == '__main__':
    unittest.main()

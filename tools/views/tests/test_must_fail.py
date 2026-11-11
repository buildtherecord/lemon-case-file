"""Records that must be refused, each with the sentence it must produce. Nothing may be written when a record is refused, and none may crash."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))  # so these run from tests/, tools/views or the repo root
import json, os, unittest

from tests import make_fixtures
from tests.helpers import HERE, Base, run, tmpdir, read

FIX = os.path.join(HERE, 'fixtures', 'must_fail')
TOOLS = {'views': 'build_views.py', 'home': 'build_home.py'}


class MustFail(Base):
    def test_every_record_is_refused_with_its_sentence_and_writes_nothing(self):
        expect = json.loads(read(os.path.join(FIX, 'EXPECT.json')))
        self.assertGreaterEqual(len(expect), 45)
        for name, e in sorted(expect.items()):
            for tool in e['tools']:
                with self.subTest(record=name, builder=tool):
                    out = os.path.join(tmpdir(), 'out')
                    code, o = run(TOOLS[tool], os.path.join(FIX, name), out, *e['args'])
                    self.assertEqual(code, 1, o)
                    self.has(e['contains'], o)
                    self.lacks('Traceback', o)
                    self.assertFalse(os.path.exists(out), 'a refused record must write nothing')
                    self.assertFalse(os.path.exists(out + '-private'))

    def test_the_required_cases_are_all_there(self):
        names = set(json.loads(read(os.path.join(FIX, 'EXPECT.json'))))
        for need in ('dollar_figure_not_in_cited_exhibit', 'typed_count_repair_orders', 'prognosis_will_likely_win', 'documented_fact_not_shown_by_document', 'miles_reading_not_in_exhibit',
                     'advice_wording', 'quote_drops_not', 'documented_no_source', 'computed_deadline', 'unsafe_id', 'script_in_title', 'typed_count', 'private_host_link_outward'):
            self.assertIn(need + '.json', names)

    def test_the_records_that_must_pass_build_under_strict_in_both_builders(self):
        """The accepted spellings of what the must-fail records get wrong."""
        rec = make_fixtures.base()
        rec['exhibits'][0]['text'] += ' Odometer in 48,210. Odometer out 48,222. Nine repair orders were listed.'
        rec['exhibits'][1]['text'] = 'We ask for a review. Pay the balance unless the vehicle is returned. The deadline is October 7.'
        rec['facts'][0]['text'] = 'The repair order shows an estimate to rebuild of $4,800.00 and {miles:E1:48,210:48,222} miles between the odometer readings. It lists nine repair orders.'
        rec['facts'][1]['text'] = 'The letter says \u201cPay the balance unless the vehicle is returned\u201d and \u201cThe deadline is October 7.\u201d The owner asked for a review.'
        rec['meta']['summary'] = 'The repair order is dated Feb 10, 2026 and the letter March 1, 2026. This page holds {count:facts} entries.'
        d = tmpdir()
        path = os.path.join(d, 'accepted.json')
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(rec, fh)
        for tool in TOOLS.values():
            code, o = run(tool, path, os.path.join(d, tool), '--strict')
            self.assertEqual(code, 0, o)
        self.assertIn('12 miles between', read(os.path.join(d, 'build_home.py', 'index.html')))

    def test_the_clean_base_record_builds(self):
        d = tmpdir()
        path = os.path.join(d, 'base.json')
        with open(path, 'w') as fh:
            json.dump(make_fixtures.base(), fh)
        for tool in TOOLS.values():
            code, o = run(tool, path, os.path.join(d, tool), '--strict')
            self.assertEqual(code, 0, o)

    def test_the_fixture_files_match_the_script_that_writes_them(self):
        for name, (f, tools, contains) in make_fixtures.CASES.items():
            on_disk = json.loads(read(os.path.join(FIX, name + '.json')))
            self.assertEqual(on_disk, make_fixtures.change(f), f'{name}.json is out of date; run python3 -m tests.make_fixtures')
        self.assertEqual(set(json.loads(read(os.path.join(FIX, 'EXPECT.json')))), {n + '.json' for n in make_fixtures.CASES})

    def test_a_script_tag_in_a_title_is_refused_and_if_it_ever_reached_the_page_it_could_not_close_the_data_block(self):
        from btr_common import script_json
        blob = script_json({'title': '</script><script>alert(1)</script> <!-- & <img>'})
        for bad in ('<', '>', '&'):
            self.assertNotIn(bad, blob)
        self.assertEqual(json.loads(blob)['title'], '</script><script>alert(1)</script> <!-- & <img>')


if __name__ == '__main__':
    unittest.main()

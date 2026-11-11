"""The shared checker: quotes, wording, typed numbers, placeholders, ids, dates, deadlines, statuses, schema, and 'never a traceback'."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))  # so these run from tests/, tools/views or the repo root
import copy, json, os, unittest

from tests.helpers import checks, HAVE_PIL, seed_record, seeds, VIEWS
from tests import make_fixtures


def good():
    return make_fixtures.base()


def errors(rec, mode='record', strict=False):
    _n, R = checks.check_record(rec, mode, strict)
    return R


class QuoteChecking(unittest.TestCase):
    T = ('Technician was unable to verify the concern. Vehicle not operating normally. The balance remains unpaid in full. Estimate to rebuild: $4,800. '
         'We do not merit a settlement offer at this time. Retainer is non-refundable except as stated.')

    def v(self, q):
        return checks.verify_quote(q, self.T)[0]

    def test_exact_words_pass_ignoring_case_spacing_and_quote_style(self):
        self.assertEqual(self.v('VEHICLE   not\n operating normally'), 'ok')
        self.assertEqual(checks.verify_quote('the owner’s “car”', 'The owner\'s "car" was here')[0], 'ok')

    def test_dropping_un_fails(self):
        self.assertEqual(self.v('able to verify the concern'), 'missing')

    def test_dropping_not_fails(self):
        self.assertEqual(self.v('operating normally'), 'negation')
        self.assertEqual(self.v('merit a settlement offer at this time'), 'negation')

    def test_stopping_just_before_not_fails(self):
        self.assertEqual(checks.verify_quote('We will', 'We will not refund this')[0], 'negation')

    def test_fragments_of_words_fail(self):
        self.assertEqual(self.v('paid in full'), 'missing')
        self.assertEqual(self.v('refundable except as stated'), 'missing')

    def test_numbers_keep_their_punctuation(self):
        self.assertEqual(self.v('Estimate to rebuild: $4,800'), 'ok')
        self.assertEqual(self.v('Estimate to rebuild: $48.00'), 'missing')
        self.assertEqual(self.v('Estimate to rebuild: $4'), 'missing')

    def test_ellipsis_joins_pieces_in_order(self):
        self.assertEqual(self.v('unable to verify … operating normally'), 'ok')
        self.assertEqual(self.v('operating normally … unable to verify'), 'missing')

    def test_extract_quotes_reads_curly_and_straight(self):
        self.assertEqual(checks.extract_quotes('He said “not now” and "never again".'), ['not now', 'never again'])


class Wording(unittest.TestCase):
    def test_advice_is_found_in_what_the_claimant_wrote(self):
        kinds = [k for k, _s, _w in checks.lint_authored('This is a strong case and you should sue.')]
        self.assertEqual(kinds, ['advice', 'advice'])

    def test_quoted_words_are_never_linted(self):
        self.assertEqual(checks.lint_authored('The letter says “too late” and “we guarantee all work.”'), [])

    def test_advocacy_is_found(self):
        self.assertTrue(checks.lint_authored('The dealer clearly lied.'))

    def test_a_statute_name_is_not_advocacy(self):
        self.assertEqual(checks.lint_authored('The owners cite the Consumer Fraud Act.'), [])

    def test_exhibit_text_is_not_linted_so_a_quote_of_a_guarantee_builds(self):
        rec = good()
        rec['exhibits'][0]['text'] += ' We guarantee all work. Too late.'
        rec['facts'][0]['sources'][0]['quote'] = 'We guarantee all work.'
        self.assertTrue(errors(rec).ok)

    def test_case_banned_words(self):
        self.assertEqual([k for k, _s, _w in checks.lint_authored('The owner asks for a review', banned=['review'])], ['banned'])

    def test_advice_in_a_fact_is_an_error_naming_the_fact(self):
        rec = good()
        rec['facts'][1]['text'] = 'The deadline has passed.'
        R = errors(rec)
        self.assertTrue(any(e.startswith('fact F2:') and 'deadline' in e for e in R.errors), R.errors)


class TypedNumbers(unittest.TestCase):
    def test_detector(self):
        self.assertEqual(checks.typed_counts('stayed 177 days; twelve times; a 60-day review; 3,700 miles; seven separate visits'),
                         ['177 days', 'twelve times', '60-day', '3,700 miles', 'seven separate visits'])

    def test_quotes_placeholders_and_adjectives_are_left_alone(self):
        self.assertEqual(checks.typed_counts('The letter says “within 180 days.” That is {days:F1:F2} days. A one-time fee. Day 114.'), [])

    def test_a_figure_the_cited_document_states_is_allowed_in_a_fact(self):
        rec = good()
        rec['exhibits'][1]['text'] = 'You may appeal within 180 days of this letter.'
        rec['facts'][1]['text'] = 'The letter says an appeal may be made within 180 days of the letter.'
        self.assertTrue(errors(rec).ok)
        rec['facts'][1]['text'] = 'The letter says an appeal may be made within 90 days of the letter.'
        self.assertFalse(errors(rec).ok)

    def test_typed_count_in_summary_fails(self):
        rec = good()
        rec['meta']['summary'] = 'The car was at the dealer for 177 days.'
        R = errors(rec)
        self.assertTrue(any('177 days' in e and 'typed' in e for e in R.errors))


class Placeholders(unittest.TestCase):
    def test_filled_from_the_record(self):
        rec = good()
        rec['meta']['summary'] = 'The letter came {days:F1:F2} days after the repair order. The page holds {count:facts} entries.'
        rec['intervals'] = [{'id': 'gap', 'label': 'Gap', 'a': 'F1', 'b': 'F2'}]
        n, R = checks.check_record(rec)
        self.assertTrue(R.ok, R.errors)
        by = {f['id']: f for f in n['facts']}
        r = checks.make_resolver(by, {'gap': n['intervals'][0]}, {'facts': 2})
        self.assertEqual(checks.expand(n['meta']['summary'], r), 'The letter came 19 days after the repair order. The page holds 2 entries.')

    def test_bad_placeholders_are_named(self):
        for text, part in (('{days:F1}', 'two fact ids'), ('{days:F1:F9}', 'not a fact'), ('{count:lemons}', 'not a count'), ('{interval:nope}', 'interval id'), ('{what:x}', 'not a placeholder')):
            rec = good()
            rec['meta']['summary'] = text
            R = errors(rec)
            self.assertTrue(any(part in e for e in R.errors), (text, R.errors))

    def test_days_must_run_forward(self):
        rec = good()
        rec['meta']['summary'] = '{days:F2:F1}'
        self.assertTrue(any('comes before' in e for e in errors(rec).errors))

    def test_outward_days_cannot_leak_an_unreleased_date(self):
        rec = good()
        rec['facts'][0]['outward'] = False
        rec['meta']['summary'] = '{days:F1:F2}'
        self.assertTrue(any('leak' in e for e in errors(rec, 'outward').errors))


class Ids(unittest.TestCase):
    def test_unsafe_ids_are_refused_everywhere(self):
        for coll, key in (('facts', 'id'), ('exhibits', 'id'), ('people', 'id'), ('issues', 'id')):
            rec = good()
            rec[coll][0][key] = 'a/b'
            self.assertFalse(errors(rec).ok, coll)

    def test_references_must_be_safe_too(self):
        rec = good()
        rec['facts'][0]['sources'] = [{'ex': '../x'}]
        self.assertFalse(errors(rec).ok)

    def test_duplicates_and_capitals(self):
        rec = good()
        rec['facts'][1]['id'] = 'F1'
        self.assertTrue(any('used twice' in e for e in errors(rec).errors))
        rec = good()
        rec['facts'][1]['id'] = 'f1'
        self.assertTrue(any('differ only by capitals' in e for e in errors(rec).errors))


class Dates(unittest.TestCase):
    def test_month_and_year_dates_are_never_padded_to_the_first(self):
        from btr_common import fmt_date
        self.assertEqual(fmt_date('2024-10'), 'October 2024')
        self.assertEqual(fmt_date('2024-10-01', 'month'), 'October 2024')
        self.assertEqual(fmt_date('2024'), '2024')
        self.assertEqual(fmt_date('2024-10-05'), 'Oct 5, 2024')

    def test_section_label_comes_from_its_own_dates(self):
        from btr_common import range_label
        self.assertEqual(range_label('2024-09-01', '2025-03-31'), 'September 2024 to March 2025')
        self.assertEqual(range_label('2025-03-01', '2025-03-31'), 'March 2025')
        self.assertEqual(range_label('2024-09-16', '2025-03-12'), 'Sep 16, 2024 to Mar 12, 2025')

    def test_precision_cannot_be_finer_than_the_date(self):
        rec = good()
        rec['facts'][0].update(date='2026-02', date_precision='day')
        self.assertTrue(any('only known to the month' in e for e in errors(rec).errors))

    def test_impossible_date_names_the_fact(self):
        rec = good()
        rec['facts'][0]['date'] = '2026-02-30'
        self.assertTrue(any(e.startswith('fact F1: date') and 'not a real date' in e for e in errors(rec).errors))


class Deadlines(unittest.TestCase):
    def test_computed_is_refused(self):
        rec = good()
        rec['deadlines'] = [{'label': 'Appeal', 'source': 'letter', 'date': '2027-03-09', 'computed': True}]
        self.assertTrue(any('never computes' in e for e in errors(rec).errors))

    def test_needs_a_source_a_date_or_the_documents_words(self):
        rec = good()
        rec['deadlines'] = [{'label': 'Appeal', 'source': 'letter'}]
        self.assertTrue(any("document's own words" in e for e in errors(rec).errors))
        rec['deadlines'] = [{'label': 'Appeal', 'wording': 'x'}]
        self.assertTrue(any("'source' is missing" in e for e in errors(rec).errors))

    def test_the_documents_words_are_checked_against_its_text(self):
        rec = good()
        rec['exhibits'][1]['text'] = 'You may appeal within 180 days of this letter.'
        rec['deadlines'] = [{'label': 'Appeal', 'source': 'letter', 'wording': 'within 180 days of this letter', 'ex': 'E2'}]
        self.assertTrue(errors(rec).ok)
        rec['deadlines'][0]['wording'] = 'within 18 days of this letter'
        self.assertTrue(any('not in E2 word for word' in e for e in errors(rec).errors))

    def test_a_date_that_is_exactly_n_days_after_the_letter_is_noted(self):
        rec = good()
        rec['deadlines'] = [{'label': 'Appeal', 'source': 'letter', 'date': '2026-08-28', 'ex': 'E2'}]  # 2026-03-01 + 180
        R = errors(rec)
        self.assertTrue(R.ok)
        self.assertTrue(any('exactly 180 days' in w for w in R.warnings))


class StatusesAndDisplay(unittest.TestCase):
    def test_documented_needs_a_document(self):
        rec = good()
        rec['facts'][1]['sources'] = []
        self.assertTrue(any('names no document' in e for e in errors(rec).errors))

    def test_open_is_a_status_and_never_reads_as_fact(self):
        rec = good()
        rec['facts'][1].update(status='open', sources=[])
        n, R = checks.check_record(rec)
        self.assertTrue(R.ok)
        ex = {e['id']: e for e in n['exhibits']}
        self.assertEqual(checks.display_status(n['facts'][1], ex)[0], 'open')
        self.assertIn('not stated as fact', checks.display_status(n['facts'][1], ex)[1])

    def test_only_the_claimants_own_documents_say_whose_document(self):
        n, R = checks.check_record(good())
        ex = {e['id']: e for e in n['exhibits']}
        self.assertEqual(checks.display_status(n['facts'][0], ex), ('documented', 'Shows in a document'))
        self.assertEqual(checks.display_status(n['facts'][1], ex), ('claimant_doc', "Per the claimant's letter of Mar 1, 2026"))
        self.assertEqual(checks.display_status(n['facts'][1], ex, "the owners'")[1], "Per the owners' letter of Mar 1, 2026")


class Gate(unittest.TestCase):
    def test_gate_needs_all_five(self):
        full = {'recipient': 'x', 'confidentiality_checked': True, 'names_checked': True, 'defamation_reminder_ack': True, 'attorney_read': True}
        self.assertEqual(checks.gate_missing({'share_gate': full}), [])
        for k in full:
            part = dict(full)
            part[k] = '' if k == 'recipient' else False
            self.assertEqual(checks.gate_missing({'share_gate': part}), [k])
        self.assertEqual(len(checks.gate_missing({})), 5)


class Schema(unittest.TestCase):
    def test_the_schema_is_valid_json_schema(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest('jsonschema is not installed')
        jsonschema.Draft202012Validator.check_schema(checks.load_schema())

    @unittest.skipUnless(HAVE_PIL, 'Pillow is needed to write the examples')
    def test_every_example_record_validates_under_both_validators(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest('jsonschema is not installed')
        v = jsonschema.Draft202012Validator(checks.load_schema())
        _d, ids = seeds()
        for id in ids:
            rec = checks.normalize(seed_record(id))
            self.assertEqual([e.message for e in v.iter_errors(rec)], [], id)
            issues = []
            schema = checks.load_schema()
            checks.validate_schema(rec, schema, schema, (), issues)
            self.assertEqual(issues, [], id)

    def test_both_validators_agree_a_bad_record_is_bad(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest('jsonschema is not installed')
        v = jsonschema.Draft202012Validator(checks.load_schema())
        for mutate in (lambda r: r['facts'][0].update(status='verified'), lambda r: r['facts'][0].pop('date'), lambda r: r['facts'][0].update(id='a b'),
                       lambda r: r['meta'].pop('updated'), lambda r: r['exhibits'][0].update(author='me')):
            rec = good()
            mutate(rec)
            issues = []
            schema = checks.load_schema()
            checks.validate_schema(checks.normalize(rec), schema, schema, (), issues)
            self.assertTrue(list(v.iter_errors(rec)) and issues)

    def test_messages_are_plain_sentences_naming_the_fact(self):
        rec = good()
        rec['facts'][0].pop('date')
        R = errors(rec)
        self.assertEqual(R.errors, ["fact F1: 'date' is missing; write it as 2026-10-04 (2026-10 for a month, 2026 for a year)."])

    def test_unknown_field_is_a_note_and_an_error_with_strict(self):
        rec = good()
        rec['facts'][0]['sourcs'] = []
        self.assertTrue(errors(rec).ok)
        self.assertTrue(any("did you mean 'sources'" in w for w in errors(rec).warnings))
        self.assertFalse(errors(rec, strict=True).ok)

    def test_nulls_are_the_same_as_missing(self):
        rec = good()
        rec['facts'][0]['time'] = None
        rec['meta']['subtitle'] = None
        self.assertTrue(errors(rec).ok)


class NeverATraceback(unittest.TestCase):
    def test_garbage_gets_sentences(self):
        junk = [None, 5, 'x', [], [1, 2], {}, {'meta': 5}, {'meta': {}, 'facts': 'x'}, {'meta': {'title': 't', 'summary': 's', 'updated': 'u'}, 'facts': [5]},
                {'meta': {'title': 't', 'summary': 's', 'updated': 'u'}, 'facts': [{}]}, {'meta': {'title': 't', 'summary': 's', 'updated': 'u'}, 'facts': [{'id': 'F1', 'date': 5, 'text': 5, 'status': []}]}]
        for j in junk:
            _n, R = checks.check_record(j)
            self.assertFalse(R.ok, j)
            self.assertTrue(all(isinstance(e, str) and e for e in R.errors))
            self.assertFalse(any('Traceback' in e for e in R.errors))

    def test_each_mutation_of_a_good_record_returns_a_result(self):
        mutations = [lambda r: r.update(spans=[{'label': 'x', 'start': '2026-01-01', 'end': 'bad'}]), lambda r: r.update(beats=[{'title': 'a', 'from': '2026-05-01', 'to': '2026-01-01'}]),
                     lambda r: r.update(intervals=[{'label': 'x', 'a': 'F1', 'b': 'F99'}]), lambda r: (r['meta'].pop('asof'), r['meta'].update(review_opened='2026-01-01')),
                     lambda r: r['facts'][0].update(excerpt_of='F9'), lambda r: r['facts'][0].update(fold_into='F1'), lambda r: r['exhibits'][0].update(file='/etc/passwd'),
                     lambda r: r['exhibits'][0].update(file='javascript:alert(1)'), lambda r: r['facts'][0].update(lane='nope')]
        for m in mutations:
            rec = good()
            m(rec)
            _n, R = checks.check_record(rec)
            self.assertFalse(R.ok)
            self.assertFalse(any('did not expect' in e for e in R.errors), R.errors)


if __name__ == '__main__':
    unittest.main()

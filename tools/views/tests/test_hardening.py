"""Gaps an independent verifier found by feeding the checker wrong records. Each gap has records that must be refused and records that must pass.

1 dollar figures   2 typed counts with other nouns   3 advice, prognosis, deadline and liability wording   4 a documented fact the document does not show
5 a quote clipped before a qualifier   6 odometer miles and clock times   7 still frames and grades   8 dates written in prose
9 running the tests from anywhere, the seed command, private hosts"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))  # so these run from tests/, tools/views or the repo root
import copy, json, os, re, subprocess, sys, unittest
from unittest import mock

from tests.helpers import checks, Base, VIEWS, needs_pillow, run, tmpdir, tree, workspace, read
from tests import make_fixtures


def good():
    return make_fixtures.base()


def R(rec, mode='record', strict=False):
    return checks.check_record(rec, mode, strict)[1]


def fact_text(rec, text, i=1, **kw):
    """Put `text` on fact F2 (default) as an account with no document, so only the wording rules look at it."""
    rec['facts'][i].update(text=text, status='account', sources=[], **kw)
    return rec


def has_error(R_, *needles):
    return any(all(n in e for n in needles) for e in R_.errors)


class DollarFigures(unittest.TestCase):
    def test_the_verifiers_two_wrong_amounts_are_refused_and_name_the_figure_and_the_fact(self):
        for wrong in ('$48.00', '$480,000'):
            rec = good()
            rec['facts'][0]['text'] = f'The estimate to rebuild was {wrong}.'  # F1 cites E1, which has no quote and states $4,800
            r = R(rec)
            self.assertTrue(has_error(r, 'fact F1', wrong, 'not in the document'), (wrong, r.errors))

    def test_the_same_amount_written_the_way_the_document_writes_it_passes(self):
        for ok in ('$4,800', '$4800', '$4,800.00', '$4800.00'):
            rec = good()
            rec['facts'][0]['text'] = f'The estimate to rebuild was {ok}.'
            self.assertTrue(R(rec, strict=True).ok, ok)

    def test_an_amount_in_another_exhibit_does_not_count_for_this_fact(self):
        rec = good()
        rec['facts'][1]['text'] = 'The owner wrote about the $4,800 estimate.'  # F2 cites E2, which has no amount
        self.assertTrue(has_error(R(rec), 'fact F2', '$4,800', 'E2'))

    def test_a_summary_amount_must_be_in_some_document(self):
        rec = good()
        rec['meta']['summary'] = 'The estimate to rebuild was $480,000.'
        self.assertTrue(has_error(R(rec), "the record's summary", '$480,000', 'any document'))
        rec['meta']['summary'] = 'The estimate to rebuild was $4,800.'
        self.assertTrue(R(rec, strict=True).ok)

    def test_a_quoted_amount_is_left_to_the_quote_check_and_a_wrong_quote_still_fails(self):
        rec = good()
        rec['facts'][0]['text'] = 'The repair order says “Estimate to rebuild: $4,800.”'
        self.assertTrue(R(rec, strict=True).ok)
        rec['facts'][0]['text'] = 'The repair order says “Estimate to rebuild: $48.00.”'
        self.assertTrue(has_error(R(rec), 'not in'))

    def test_a_cited_document_with_no_text_cannot_confirm_the_figure(self):
        rec = good()
        rec['exhibits'][0].pop('text')
        rec['facts'][0]['text'] = 'The estimate to rebuild was $4,800.'
        r = R(rec)
        self.assertTrue(r.ok)
        self.assertTrue(any('cannot be checked' in w and '$4,800' in w for w in r.warnings), r.warnings)
        self.assertTrue(has_error(R(rec, strict=True), '$4,800', 'cannot be checked'))

    def test_an_account_with_no_document_may_state_an_amount_and_the_claimants_own_entries_are_left_alone(self):
        rec = fact_text(good(), 'The owner says the dealer asked for $9,999 by phone.')
        rec['meta']['amount'] = '$999,999'
        rec['meta']['ask'] = 'A refund of $999,999'
        self.assertTrue(R(rec, strict=True).ok)

    def test_a_placeholder_is_never_read_as_a_dollar_figure(self):
        rec = good()
        rec['meta']['summary'] = 'The page holds ${count:facts} dated entries.'
        self.assertFalse(has_error(R(rec), 'the figure'))


class TypedCountsWithOtherNouns(unittest.TestCase):
    WRONG = ['nine repair orders', 'seven repair orders', 'nine repair attempts', 'nineteen stored faults', 'fifteen stored faults', '3 trips', '12 emails', '4 entries', '1 entry',
             '2 incidents', '5 occasions', '6 appointments', '7 actions', '8 messages', '9 calls', '10 items', '11 pages', '12 photos', '13 videos', '14 clips', '15 texts',
             '16 letters', '17 notices', 'six more repair orders', 'two separate stored faults', 'four e-mails', 'twenty-one photos', 'a dozen calls']

    def test_every_one_is_found_and_refused_naming_the_fact(self):
        for phrase in self.WRONG:
            with self.subTest(phrase=phrase):
                found = checks.typed_counts(f'The owner made {phrase} that month.')
                self.assertEqual(len(found), 1, found)
                self.assertIn(found[0], phrase)
                rec = fact_text(good(), f'The owner made {phrase} that month.')
                self.assertTrue(has_error(R(rec), 'fact F2', found[0], 'typed into the text'))

    def test_the_old_nouns_still_work_with_a_modifier_word(self):
        self.assertEqual(checks.typed_counts('stayed 177 days; twelve times; a 60-day review; 3,700 miles; seven separate visits'),
                         ['177 days', 'twelve times', '60-day', '3,700 miles', 'seven separate visits'])
        self.assertEqual(checks.typed_counts('Nineteen stored faults and four recorded days.'), ['Nineteen stored faults', 'four recorded days'])

    def test_quoted_spans_cited_exhibit_figures_and_placeholders_are_exempt(self):
        rec = good()
        rec['exhibits'][1]['text'] = 'We ask for a review of the nine repair orders.'
        rec['facts'][1]['text'] = 'The letter says “the nine repair orders.”'
        self.assertTrue(R(rec, strict=True).ok)
        rec['facts'][1]['text'] = 'The letter asks for a review of the nine repair orders.'  # the cited document states it in its own words
        self.assertTrue(R(rec, strict=True).ok)
        rec['facts'][1]['text'] = 'The letter asks for a review of the eight repair orders.'
        self.assertTrue(has_error(R(rec), 'eight repair orders'))
        rec = good()
        rec['meta']['summary'] = 'The page holds {count:facts} entries and {count:documents} documents. It is {days:F1:F2} days between them.'
        self.assertTrue(R(rec, strict=True).ok)

    def test_a_clock_time_a_year_an_adjective_and_no_one_are_not_counts(self):
        for ok in ('The 11:18 recording shows the display.', 'The 11:18 AM recordings.', 'At 9:05:33 videos were uploaded.', 'The 2025 letters are filed.', 'A one-page letter.',
                   'No one calls back.', 'On 2026-03-12 messages arrived.', 'It was 1 pm calls started.', 'Three of the calls were missed.',
                   "VW's September 28 message arrived.", 'The Sep. 3 calls were logged.', 'Their one-on-one texts are filed.', 'A two-way calls log.'):
            with self.subTest(text=ok):
                self.assertEqual(checks.typed_counts(ok), [])

    def test_a_range_is_still_a_count_and_a_hyphenated_unit_is_still_a_count(self):
        self.assertEqual(checks.typed_counts('Made 3-4 visits and a 12-page letter and a 60-day review.'), ['4 visits', '12-page', '60-day'])

    def test_a_time_before_a_recording_is_not_read_as_a_count_by_the_checker(self):
        rec = fact_text(good(), 'The owner made an 11:18 recording of the display.')
        self.assertFalse(has_error(R(rec), 'typed into the text'))


class AdviceAndAdvocacyWording(unittest.TestCase):
    PROGNOSIS = ['The owner will likely win.', 'The owner has a good chance.', 'The owner will probably win this.', 'The claim should prevail.', 'The odds are on the owner.',
                 'The owner has a strong chance of success.', 'The owner could lose.', 'Chances of winning are small.', 'The owner will most likely recover everything.']
    DEADLINE = ['The deadline is October 7.', 'The owner must file by October 7.', 'The owner has until October 7.', 'The statute of limitations expires in March.',
                'The filing deadline for the claim is soon.', 'The appeal must be filed within 30 days.']
    LIABILITY = ['The dealer is liable for the repair.', 'The dealer broke the law.', 'The dealer acted illegally.', 'The sale was illegal.', 'The manufacturer is at fault.',
                 'The dealer is legally responsible.', 'The dealer breached the law.']
    HIRE = ['The owner should hire a lawyer.', 'You should consult an attorney.', 'The owner should talk to a lawyer.', 'They need to retain counsel.', 'You must contact a lawyer.']

    def test_every_phrase_is_refused_in_what_the_claimant_wrote(self):
        for group in (self.PROGNOSIS, self.DEADLINE, self.LIABILITY, self.HIRE):
            for text in group:
                with self.subTest(text=text):
                    self.assertTrue(checks.lint_authored(text), text)
                    rec = fact_text(good(), text)
                    self.assertTrue(has_error(R(rec), 'fact F2', 'wording the tool does not use'), R(rec).errors)

    def test_the_same_words_quoted_from_a_document_pass(self):
        for text in self.PROGNOSIS + self.DEADLINE + self.LIABILITY + self.HIRE:
            with self.subTest(text=text):
                rec = good()
                rec['exhibits'][1]['text'] = 'We ask for a review. ' + text
                rec['facts'][1]['text'] = f'The letter says “{text}”'
                self.assertEqual(checks.lint_authored(rec['facts'][1]['text']), [])
                self.assertTrue(R(rec, strict=True).ok, R(rec, strict=True).errors)

    def test_words_in_an_exhibits_own_text_are_never_linted(self):
        rec = good()
        rec['exhibits'][1]['text'] += ' The deadline is October 7. The dealer is liable. You will likely win.'
        self.assertTrue(R(rec, strict=True).ok)

    def test_plain_reporting_of_what_is_missing_or_stated_passes(self):
        for ok in ('No document states what the deadline is.', 'The letter gives a deadline of 180 days.', 'The owner wrote a letter asking for a review.',
                   'The dealer wrote that the vehicle was not operating normally.', 'The two accounts are at odds.', 'The owner asks whether a lawyer is needed.'):
            with self.subTest(text=ok):
                self.assertEqual(checks.lint_authored(ok), [])

    def test_the_same_words_are_refused_in_a_summary_a_beat_and_a_span_note(self):
        for put in (lambda r, t: r['meta'].update(summary=t), lambda r, t: r.update(beats=[{'title': 'The letter', 'from': '2026-03-01', 'to': '2026-03-31', 'prose': [t]}]),
                    lambda r, t: r.update(spans=[{'label': 'Review', 'start': '2026-02-10', 'end': '2026-03-01', 'note': t}])):
            rec = good()
            put(rec, 'The owner will likely win.')
            self.assertTrue(has_error(R(rec), 'wording the tool does not use', 'will likely win'))

    def test_the_old_rules_still_stand(self):
        kinds = [k for k, _s, _w in checks.lint_authored('This is a strong case and you should sue.')]
        self.assertEqual(kinds, ['advice', 'advice'])
        self.assertTrue(checks.lint_authored('The dealer clearly lied.'))
        self.assertEqual(checks.lint_authored('The letter says “too late” and “we guarantee all work.”'), [])


class DocumentedFactsMustBeShownByTheirDocument(unittest.TestCase):
    def test_a_fact_that_shares_nothing_with_its_document_is_refused_with_the_plain_sentence(self):
        rec = good()
        rec['facts'][1]['text'] = 'The dealer replaced the transmission on March 12.'  # F2 cites E2: 'We ask for a review.'
        r = R(rec)
        self.assertTrue(has_error(r, 'fact F2 is marked documented but its cited document does not appear to show it'), r.errors)

    def test_a_fact_that_shares_a_word_a_number_or_a_name_passes(self):
        for text in ('The owner asked for a review.', 'The owner wrote a letter asking for a review.', 'The dealer wrote a review.'):
            rec = good()
            rec['facts'][1]['text'] = text
            self.assertTrue(R(rec, strict=True).ok, text)
        rec = good()
        rec['exhibits'][1]['text'] = 'Repair order RO306607. Mileage in 48,210. Signed by Hernandez.'
        for text in ('The dealer wrote up RO306607.', 'The reading was 48210.', 'The service writer, Hernandez, signed it.', 'The paper has RO306607 on it.'):
            rec['facts'][1]['text'] = text
            self.assertTrue(R(rec, strict=True).ok, text)

    def test_the_escape_hatch_is_a_place_and_a_quote_that_is_in_the_document(self):
        rec = good()
        rec['facts'][1]['text'] = 'The dealer replaced the transmission on March 12.'
        rec['facts'][1]['sources'][0].update(loc='page 1', quote='We ask for a review.')
        self.assertTrue(R(rec, strict=True).ok)
        rec['facts'][1]['sources'][0].pop('loc')  # a quote with no place is not the escape hatch
        self.assertTrue(has_error(R(rec), 'does not appear to show it'))
        rec['facts'][1]['sources'][0].update(loc='page 1', quote='We demand a refund.')  # and a quote that is not in the document is refused outright
        self.assertTrue(has_error(R(rec), 'not in E2 word for word'))

    def test_only_documented_facts_are_compared_and_only_when_every_cited_document_has_text(self):
        rec = good()
        rec['facts'][1].update(text='The dealer replaced the transmission on March 12.', status='account')
        self.assertTrue(R(rec, strict=True).ok)
        rec = good()
        rec['facts'][1]['text'] = 'The dealer replaced the transmission on March 12.'
        rec['exhibits'][1].pop('text')
        self.assertTrue(R(rec).ok)
        rec = good()
        rec['facts'][1]['text'] = 'The dealer replaced the transmission on March 12.'
        rec['exhibits'].append({'id': 'E3', 'title': 'Photo', 'date': '2026-03-01', 'author': 'claimant'})
        rec['facts'][1]['sources'].append({'ex': 'E3'})
        self.assertTrue(R(rec).ok)  # one cited document has no text, so it may be the one that shows it

    def test_a_fact_with_nothing_distinctive_in_it_is_not_refused(self):
        rec = good()
        rec['facts'][1]['text'] = 'It was in the file.'
        self.assertTrue(R(rec, strict=True).ok)

    def test_the_miles_in_the_other_direction_a_different_document_does_not_show_it(self):
        rec = good()
        rec['facts'][0]['sources'] = [{'ex': 'E2'}]  # F1 is about the repair order, but cites the owner's letter
        self.assertTrue(has_error(R(rec), 'fact F1 is marked documented but its cited document'))


class ClippedQuotes(unittest.TestCase):
    TEXT = 'Pay the balance unless the vehicle is returned. Next sentence.'

    def rec(self, quote, text=None):
        rec = good()
        rec['exhibits'][1]['text'] = text or self.TEXT
        rec['facts'][1]['text'] = f'The owner was told to “{quote}” in a letter.'
        return rec

    def test_a_quote_that_stops_before_unless_is_a_note_and_an_error_with_strict(self):
        rec = self.rec('Pay the balance')
        r = R(rec)
        self.assertTrue(r.ok)
        self.assertTrue(any("stop right before 'unless'" in w for w in r.warnings), r.warnings)
        self.assertTrue(has_error(R(rec, strict=True), "stop right before 'unless'", 'fact F2'))

    def test_each_qualifier_is_caught(self):
        for word in ('if', 'or', 'unless', 'until', 'but', 'except', 'provided'):
            with self.subTest(word=word):
                r = R(self.rec('Pay the balance', f'Pay the balance {word} the vehicle is returned.'), strict=True)
                self.assertTrue(has_error(r, f"stop right before '{word}'"), r.errors)
        r = R(self.rec('Pay the balance', 'Pay the balance, unless the vehicle is returned.'), strict=True)  # a comma does not hide it
        self.assertTrue(has_error(r, "'unless'"))

    def test_the_whole_sentence_an_ellipsis_or_a_sentence_end_pass(self):
        for quote, text in (('Pay the balance unless the vehicle is returned', self.TEXT), ('Pay the balance …', self.TEXT), ('Pay the balance...', self.TEXT),
                            ('Pay the balance', 'Pay the balance. Unless told otherwise, wait.'), ('Pay the balance', 'Pay the balance'), ('Pay the balance', 'Pay the balance on time.')):
            with self.subTest(quote=quote, text=text):
                self.assertTrue(R(self.rec(quote, text), strict=True).ok, R(self.rec(quote, text), strict=True).errors)

    def test_a_quote_that_appears_whole_somewhere_else_passes(self):
        text = 'Pay the balance unless the vehicle is returned. Later it says: Pay the balance. Done.'
        self.assertTrue(R(self.rec('Pay the balance', text), strict=True).ok)

    def test_a_source_quote_is_checked_the_same_way_and_the_old_negation_rule_still_wins(self):
        rec = good()
        rec['exhibits'][1]['text'] = self.TEXT
        rec['facts'][1]['text'] = 'The owner was told to pay the balance.'
        rec['facts'][1]['sources'][0]['quote'] = 'Pay the balance'
        self.assertTrue(has_error(R(rec, strict=True), 'the quote from E2 stops right before'))
        self.assertTrue(R(rec).ok, R(rec).errors)
        self.assertEqual(checks.clipped_before('operating normally', 'Vehicle not operating normally.'), None)
        self.assertEqual(checks.verify_quote('operating normally', 'Vehicle not operating normally.')[0], 'negation')


class Miles(unittest.TestCase):
    def rec(self, args='E1:48,210:48,222', text=None):
        rec = good()
        rec['exhibits'][0]['text'] += ' Odometer in 48,210. Odometer out 48,222. Repair order RO306607.'
        rec['facts'][0]['text'] = text or ('The repair order RO306607 shows {miles:%s} miles on the odometer between Feb 10, 2026 and Mar 1, 2026.' % args)
        return rec

    def test_the_difference_is_computed_from_two_numbers_in_the_cited_exhibit(self):
        rec = self.rec()
        n, r = checks.check_record(rec, strict=True)
        self.assertTrue(r.ok, r.errors)
        by = {f['id']: f for f in n['facts']}
        ex = {e['id']: e for e in n['exhibits']}
        text = checks.expand(n['facts'][0]['text'], checks.make_resolver(by, {}, {}, ex))
        self.assertIn('shows 12 miles on the odometer', text)
        self.assertEqual(checks.make_resolver(by, {}, {}, ex)('miles', ['E1', '48210', '48222']), '12')
        self.assertEqual(checks.make_resolver(by, {}, {}, {'E1': {'text': 'in 100 out 1,500'}})('miles', ['E1', '100', '1,500']), '1,400')

    def test_wrong_miles_are_refused_with_a_sentence_naming_the_fact(self):
        cases = {'E1:48,210:48,999': 'the reading 48,999 is not in exhibit E1', 'E1:48,222:48,210': 'is not larger than the first', 'E9:1:2': 'not an exhibit',
                 'E1:48,210': 'needs an exhibit id and two odometer readings', 'E1:abc:48,222': 'must be whole numbers', 'E1:48,210:48,210': 'is not larger',
                 'E2:48,210:48,222': 'is not in exhibit E2'}
        for args, part in cases.items():
            with self.subTest(args=args):
                r = R(self.rec(args))
                self.assertTrue(has_error(r, 'fact F1', part), r.errors)

    def test_an_exhibit_with_no_text_cannot_confirm_the_readings(self):
        rec = self.rec()
        rec['exhibits'][0].pop('text')
        self.assertTrue(has_error(R(rec), 'has no text to find the readings in'))

    def test_a_reading_that_is_only_part_of_a_longer_number_is_not_found(self):
        rec = self.rec('E1:4,821:4,822')
        rec['exhibits'][0]['text'] += ' Part 48210X. Serial 148,2100.'
        self.assertTrue(has_error(R(rec), 'is not in exhibit E1'))

    def test_the_resolver_refuses_when_it_is_not_given_the_exhibits(self):
        with self.assertRaises(checks.BuildError):
            checks.make_resolver({}, {}, {})('miles', ['E1', '1', '2'])

    def test_on_the_outward_page_the_exhibit_should_be_shared_so_a_reader_can_check(self):
        rec = self.rec()
        rec['exhibits'][0]['share'] = False
        r = R(rec, 'outward')
        self.assertTrue(any('not shared' in w for w in r.warnings), r.warnings)
        self.assertTrue(has_error(R(rec, 'outward', True), 'not shared'))
        rec['exhibits'][0]['share'] = True
        self.assertFalse(any('not shared' in w for w in R(rec, 'outward').warnings))

    @needs_pillow
    def test_both_builders_fill_it_in(self):
        w = workspace('FULL1')
        self.assertEqual(w.home('--strict')[0], 0)
        self.assertIn('two odometer readings, 11 miles apart', w.page())
        self.assertEqual(w.views('--strict')[0], 0)
        w.fact('F3')['text'] = 'Second visit: the dealer replaced the display unit; the car shows {miles:E3:4,120:4,131} miles on the odometer.'
        self.assertEqual(w.home('--strict')[0], 0)
        self.assertIn('the car shows 11 miles on the odometer', w.page())
        self.assertEqual(w.views('--strict')[0], 0)
        self.assertIn('the car shows 11 miles on the odometer', ' '.join(v.decode() for k, v in tree(os.path.join(w.folder, 'inward')).items() if k.endswith('.html')))
        w.fact('F3')['text'] = 'Second visit: the dealer replaced the display unit; the car shows {miles:E3:4,120:9,999} miles.'
        code, o = w.home('--strict', out=os.path.join(w.folder, 'o2'))
        self.assertEqual(code, 1)
        self.assertIn('the reading 9,999 is not in exhibit E3', o)
        self.assertFalse(os.path.exists(os.path.join(w.folder, 'o2')))


class StillFrames(unittest.TestCase):
    def rec(self, grade=None, by=None, still_kind='Still frame from a recording', facts_cite='R1'):
        rec = good()
        rec['exhibits'] += [
            {'id': 'R1', 'title': 'Clip', 'date': '2026-02-10', 'kind': 'Video', 'author': 'claimant', 'share': False, 'file': 'R1.mp4'},
            {'id': 'X1', 'title': 'Still', 'date': '2026-02-10', 'kind': still_kind, 'author': 'claimant', 'share': True, 'feature': True, 'caption': 'A frame of the clip', 'excerpt_of': 'R1'}]
        f = {'id': 'F3', 'date': '2026-02-10', 'text': 'The clip shows the display going black.', 'status': 'account', 'sources': [{'ex': facts_cite}], 'outward': True}
        if grade:
            f['grade'] = grade
        if by:
            f['reviewed_by'] = by
        rec['facts'].append(f)
        return rec

    def test_a_featured_still_of_a_recording_with_an_unconfirmed_grade_is_a_note_and_an_error_with_strict(self):
        for by in ('assistant', None):
            rec = self.rec('A', by)
            r = R(rec, 'outward')
            self.assertTrue(r.ok, r.errors)
            self.assertTrue(any('X1 is a featured still frame of recording R1' in w and 'has not confirmed' in w for w in r.warnings), r.warnings)
            self.assertTrue(has_error(R(rec, 'outward', True), 'exhibit X1', 'fact F3 gives it grade A', 'has not confirmed'))

    def test_a_still_whose_recording_the_owner_confirmed_passes(self):
        self.assertFalse(has_error(R(self.rec('A', 'owner'), 'outward', True), 'X1'))

    def test_a_still_with_no_grade_anywhere_is_not_an_error(self):
        r = R(self.rec(), 'outward', True)
        self.assertFalse(has_error(r, 'X1'), r.errors)
        rec = self.rec()
        rec['facts'].pop()  # and no fact cites the recording at all
        self.assertFalse(has_error(R(rec, 'outward', True), 'X1'))

    def test_a_still_is_not_held_to_the_featured_recording_rule(self):
        # a kind that starts with 'recording' used to make a still look like a recording that has no grade
        r = R(self.rec(still_kind='Recording still frame'), 'outward', True)
        self.assertFalse(has_error(r, 'X1', 'featured recording'), r.errors)

    def test_a_featured_recording_itself_still_needs_the_owners_grade(self):
        rec = self.rec()
        rec['exhibits'][2].update(share=True, feature=True, caption='The clip')
        rec['exhibits'][3].pop('feature')
        self.assertTrue(has_error(R(rec, 'outward', True), 'R1 is a featured recording'))
        rec['facts'][2].update(grade='A', reviewed_by='owner')
        self.assertFalse(has_error(R(rec, 'outward', True), 'R1 is a featured recording'))

    def test_a_grade_on_a_fact_that_cites_the_still_itself_counts_too(self):
        rec = self.rec('B', 'assistant', facts_cite='X1')
        self.assertTrue(has_error(R(rec, 'outward', True), 'exhibit X1', 'grade B'))

    def test_the_grade_check_reads_the_recording_through_an_excerpt(self):
        rec = self.rec('A', 'assistant')
        rec['exhibits'].append({'id': 'R2', 'title': 'Excerpt of the clip', 'date': '2026-02-10', 'kind': 'Video excerpt', 'author': 'claimant', 'excerpt_of': 'R1', 'file': 'R2.mp4'})
        rec['exhibits'][3]['excerpt_of'] = 'R2'
        self.assertTrue(has_error(R(rec, 'outward', True), 'X1', 'recording R1'))


class DatesWrittenInProse(unittest.TestCase):
    def test_a_date_no_fact_has_is_refused_naming_where_it_is(self):
        for put, where in ((lambda r, t: r['meta'].update(summary=t), "the record's summary"),
                           (lambda r, t: r.update(beats=[{'title': 'The letter', 'from': '2026-03-01', 'to': '2026-03-31', 'prose': [t]}]), "section 'The letter' (paragraph 1)"),
                           (lambda r, t: r.update(beats=[{'title': 'The letter', 'from': '2026-03-01', 'to': '2026-03-31', 'line': t}]), "section 'The letter' (line)"),
                           (lambda r, t: r.update(spans=[{'label': 'Review', 'start': '2026-02-10', 'end': '2026-03-01', 'note': t}]), "span 'Review' (note)"),
                           (lambda r, t: r.update(spans=[{'label': t, 'start': '2026-02-10', 'end': '2026-03-01'}]), "(label)")):
            rec = good()
            put(rec, 'The dealer wrote on March 12, 2027.')
            r = R(rec)
            self.assertTrue(has_error(r, where, 'March 12, 2027', 'no fact, span, document or deadline'), r.errors)

    def test_dates_of_facts_spans_documents_deadlines_and_asof_pass_in_every_written_form(self):
        rec = good()
        rec['spans'] = [{'label': 'Review', 'start': '2026-04-05', 'end': '2026-04-20'}]
        rec['deadlines'] = [{'label': 'Reply', 'source': 'The letter', 'date': '2026-11-02'}]
        rec['meta']['summary'] = ('The repair order is dated Feb 10, 2026, the letter March 1, 2026 (also 1 March 2026 and 2026-03-01). The review ran April 5, 2026 to Apr 20, 2026. '
                                  'The reply date on the letter is November 2, 2026, and this page was written Oct 3, 2026.')
        self.assertTrue(R(rec, strict=True).ok, R(rec, strict=True).errors)

    def test_a_date_inside_quotation_marks_is_the_documents_not_checked_here(self):
        rec = good()
        rec['exhibits'][1]['text'] += ' Call me on March 12, 2027 about it.'
        rec['meta']['summary'] = 'The letter says “Call me on March 12, 2027 about it.”'
        self.assertTrue(R(rec, strict=True).ok, R(rec, strict=True).errors)

    def test_an_impossible_date_is_named(self):
        rec = good()
        rec['meta']['summary'] = 'It happened on February 30, 2026.'
        self.assertTrue(has_error(R(rec), 'February 30, 2026', 'not a real date'))

    def test_future_tense_about_a_past_date_is_a_note_and_an_error_with_strict(self):
        for phrase in ('A review is scheduled for March 1, 2026.', 'The meeting is set for March 1, 2026.', 'The owner will meet the dealer on March 1, 2026.'):
            with self.subTest(phrase=phrase):
                rec = good()
                rec['meta']['summary'] = phrase
                r = R(rec)
                self.assertTrue(r.ok, r.errors)
                self.assertTrue(any("a date before the record's as-of date (Oct 3, 2026)" in w for w in r.warnings), r.warnings)
                self.assertTrue(has_error(R(rec, strict=True), "a date before the record's as-of date"))

    def test_future_tense_about_a_date_still_ahead_or_with_no_asof_is_left_alone(self):
        rec = good()
        rec['facts'].append({'id': 'F3', 'date': '2026-12-01', 'text': 'The owner wrote the date of the visit.', 'status': 'account', 'outward': True})
        rec['meta']['summary'] = 'A review is scheduled for Dec 1, 2026.'
        self.assertTrue(R(rec, strict=True).ok, R(rec, strict=True).errors)
        rec = good()
        rec['meta'].pop('asof')
        rec['meta']['summary'] = 'A review is scheduled for March 1, 2026.'
        self.assertTrue(R(rec, strict=True).ok)

    def test_past_tense_about_a_past_date_passes(self):
        rec = good()
        rec['meta']['summary'] = 'The owner wrote on March 1, 2026 and the dealer on Feb 10, 2026. The review was held on March 1, 2026.'
        self.assertTrue(R(rec, strict=True).ok, R(rec, strict=True).errors)


class RunningTheTests(unittest.TestCase):
    ONE = 'test_the_required_cases_are_all_there'

    def unittest_in(self, cwd, *args):
        r = subprocess.run([sys.executable, '-m', 'unittest', *args], cwd=cwd, capture_output=True, text=True, timeout=300)
        return r.returncode, r.stdout + r.stderr

    def test_it_runs_from_the_tests_folder_the_views_folder_and_the_repository_root(self):
        tests_dir = os.path.join(VIEWS, 'tests')
        root = os.path.abspath(os.path.join(VIEWS, '..', '..'))
        for cwd, args in ((tests_dir, ['-k', self.ONE]), (tests_dir, ['test_must_fail.MustFail.' + self.ONE]), (VIEWS, ['-k', self.ONE]), (VIEWS, ['tests.test_must_fail.MustFail.' + self.ONE]),
                          (root, ['discover', '-s', os.path.join('tools', 'views', 'tests'), '-k', self.ONE]), (root, ['discover', '-s', os.path.join('tools', 'views'), '-k', self.ONE]),
                          (root, ['discover', '-s', os.path.join('tools', 'views', 'tests'), '-t', os.path.join('tools', 'views'), '-k', self.ONE])):
            with self.subTest(cwd=os.path.relpath(cwd, root), args=args):
                code, out = self.unittest_in(cwd, *args)
                self.assertEqual(code, 0, out)
                self.assertIn('Ran 1 test', out)

    def test_every_test_module_puts_the_views_folder_on_the_path_itself(self):
        for name in os.listdir(os.path.join(VIEWS, 'tests')):
            if name.startswith('test_') and name.endswith('.py'):
                self.assertIn('_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))', read(os.path.join(VIEWS, 'tests', name)), name)


class SeedCommand(unittest.TestCase):
    SEED = os.path.join(VIEWS, 'example', 'seed.py')

    def test_help_prints_help_and_writes_nothing(self):
        d = tmpdir()
        for flag in ('--help', '-h'):
            r = subprocess.run([sys.executable, self.SEED, flag], cwd=d, capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn('usage: seed.py', r.stdout)
            self.assertIn('OUTDIR', r.stdout.upper())
            self.assertEqual(os.listdir(d), [], 'help must not create any folder')

    def test_an_unknown_option_is_refused_and_writes_nothing(self):
        d = tmpdir()
        r = subprocess.run([sys.executable, self.SEED, '--nonsense'], cwd=d, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 2)
        self.assertEqual(os.listdir(d), [])

    @needs_pillow
    def test_a_folder_name_writes_the_21_records_there(self):
        d = tmpdir()
        r = subprocess.run([sys.executable, self.SEED, 'examples'], cwd=d, capture_output=True, text=True, timeout=300)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len([n for n in os.listdir(os.path.join(d, 'examples')) if n.endswith('.json')]), 21)
        self.assertEqual(os.listdir(d), ['examples'])


class PrivateHosts(Base):
    def setUp(self):
        self.d = tmpdir()
        self.file = os.path.join(self.d, 'private-hosts.txt')
        with open(self.file, 'w') as fh:
            fh.write('# sites that need a login\n*.records.example.net\nhttps://Other.Example.org/some/path  # trailing note\n\nbare.example.io\n')
        self.env = mock.patch.dict(os.environ, {'BTR_PRIVATE_HOSTS_FILE': self.file})

    def link_rec(self, host, field='link'):
        rec = good()
        rec['exhibits'][1].update({field: f'https://{host}/x'}, feature=True, caption='A letter', thumb=None if field == 'thumb' else 'https://img.example.com/t.jpg')
        if field == 'thumb':
            rec['exhibits'][1]['thumb'] = f'https://{host}/t.jpg'
        return rec

    def test_the_example_host_is_always_private_and_the_file_adds_to_it(self):
        self.assertIn('private.example.com', checks.private_hosts())
        with self.env:
            hosts = checks.private_hosts()
        for h in ('private.example.com', 'records.example.net', 'other.example.org', 'bare.example.io'):
            self.assertIn(h, hosts)
        self.assertNotIn('', hosts)

    def test_a_host_covers_itself_and_what_is_under_it_and_nothing_else(self):
        with self.env:
            for yes in ('records.example.net', 'a.b.records.example.net', 'Records.Example.NET.', 'other.example.org', 'bare.example.io', 'x.private.example.com'):
                self.assertTrue(checks.is_private_host(yes), yes)
            for no in ('example.net', 'records.example.net.evil.com', 'notrecords.example.net', 'example.com', '', None):
                self.assertFalse(checks.is_private_host(no), no)
            rx = checks.private_url_rx()
            self.assertEqual([m.group(0) for m in rx.finditer('see "https://a.records.example.net/p?q=1" and https://example.com/x')], ['https://a.records.example.net/p?q=1'])

    def test_a_shared_link_or_thumbnail_on_a_private_host_stops_the_outward_check(self):
        with self.env:
            for host in ('private.example.com', 'records.example.net', 'deep.records.example.net', 'other.example.org'):
                for field in ('link', 'thumb', 'file'):
                    with self.subTest(host=host, field=field):
                        r = R(self.link_rec(host, field), 'outward')
                        self.assertTrue(has_error(r, 'exhibit E2', field, host, 'a private site'), r.errors)

    def test_an_ordinary_host_and_an_unshared_exhibit_are_not_stopped(self):
        with self.env:
            self.assertFalse(has_error(R(self.link_rec('example.com'), 'outward'), 'private site'))
            rec = self.link_rec('records.example.net')
            rec['exhibits'][1]['share'] = False
            self.assertFalse(has_error(R(rec, 'outward'), 'private site'))

    def test_the_default_blocks_only_the_example_host_when_there_is_no_file(self):
        with mock.patch.dict(os.environ, {'BTR_PRIVATE_HOSTS_FILE': ''}), mock.patch.object(checks, 'HERE', self.d + '-none'):
            self.assertEqual(checks.private_hosts(), ['private.example.com'])

    def test_a_named_file_that_is_missing_is_a_plain_error_not_a_crash(self):
        with mock.patch.dict(os.environ, {'BTR_PRIVATE_HOSTS_FILE': os.path.join(self.d, 'nope.txt')}):
            r = R(good(), 'outward')
        self.assertTrue(has_error(r, 'private hosts file', 'was not found'), r.errors)

    @needs_pillow
    def test_the_builder_refuses_a_private_host_from_the_file_and_the_example_host(self):
        for host in ('private.example.com', 'deep.records.example.net'):
            w = workspace('FULL1')
            w.exhibit('E7')['thumb'] = f'https://{host}/t.jpg'
            with self.env:
                code, o = w.home()
            self.assertEqual(code, 1, o)
            self.has('a private site', o)
            self.assertFalse(os.path.exists(w.out))

    @needs_pillow
    def test_a_private_address_inside_a_shared_page_text_stops_or_warns_using_the_same_list(self):
        w = workspace('FULL1')
        with open(os.path.join(w.files, 'E5.html'), 'a', encoding='utf-8') as fh:
            fh.write('<p>See https://a.records.example.net/inbox</p>')
        with self.env:
            code, o = w.home()
        self.assertEqual(code, 0, o)
        self.has('a.records.example.net', w.report() + o)

    def test_the_rule_ships_with_a_gitignored_file_and_nothing_case_specific_in_the_public_files(self):
        self.has('private-hosts.txt', read(os.path.join(VIEWS, '.gitignore')))
        self.has('private-hosts.txt', read(os.path.join(VIEWS, 'README.md')))
        needle = 'caitlin' + 'everett'
        listed = set(json.loads(read(os.path.join(VIEWS, 'tests', 'fixtures', 'must_fail', 'EXPECT.json'))))
        checked = []
        for dp, dn, names in os.walk(VIEWS):
            dn[:] = [x for x in dn if x not in ('__pycache__', '--help', 'examples')]
            for n in names:
                p = os.path.join(dp, n)
                if n in ('private-hosts.txt',) or not n.endswith(('.py', '.md', '.js', '.json', '.txt', '.gitignore')):
                    continue
                if os.path.basename(dp) == 'must_fail' and n not in listed and n != 'EXPECT.json':
                    continue  # a leftover fixture from an earlier version is not one this suite writes or reads
                checked.append(p)
                self.assertNotIn(needle, read(p).lower(), os.path.relpath(p, VIEWS))
        self.assertGreater(len(checked), 20)
        self.assertNotIn(needle, read(os.path.join(VIEWS, '..', '..', 'schema', 'record.schema.json')).lower())


class WhatTheBuildChecks(unittest.TestCase):
    def table(self):
        text = read(os.path.join(VIEWS, 'README.md'))
        self.assertIn('## What the build checks', text)
        body = text.split('## What the build checks', 1)[1].split('\n## ', 1)[0]
        return [[c.strip() for c in ln.strip('|').split('|')] for ln in body.splitlines() if ln.startswith('|') and not set(ln) <= set('|- ')][1:]

    def test_every_row_has_a_status_word_and_every_new_check_is_listed(self):
        rows = self.table()
        self.assertGreaterEqual(len(rows), 14)
        for r in rows:
            self.assertRegex(r[-1], r'^(built|planned)\b', r)
        text = ' '.join(r[0] + ' ' + r[1] for r in rows).lower()
        for need in ('dollar', 'repair orders', 'prognosis', 'deadline', 'liable', 'key word', 'qualifier', 'miles', 'clock', 'still', 'dates written', 'private host'):
            self.assertIn(need, text, need)


class PlannedMeansNotBuilt(unittest.TestCase):
    """Each row the README marks planned is shown not to be done. If one gets built, this fails and the README must change with it."""

    def test_a_date_without_a_year_or_a_month_only_date_is_not_compared_with_the_record(self):
        rec = good()
        rec['meta']['summary'] = 'The dealer wrote on October 7 and again in March 2025.'
        self.assertTrue(R(rec, strict=True).ok, R(rec, strict=True).errors)

    def test_an_amount_in_words_or_another_currency_is_not_compared_with_the_documents(self):
        rec = good()
        rec['facts'][0]['text'] = 'The estimate to rebuild was forty-eight dollars, or 480 euros, or \u00a3500.'
        self.assertFalse(has_error(R(rec), 'the figure'), R(rec).errors)

    def test_the_claimants_own_ask_and_amount_are_not_compared_with_the_documents(self):
        rec = good()
        rec['meta'].update(ask='A refund of $999,999', amount='$999,999')
        self.assertTrue(R(rec, strict=True).ok)

    def test_a_fact_that_reuses_the_documents_words_but_reverses_them_is_not_caught_by_the_key_word_test(self):
        rec = good()
        rec['facts'][0]['text'] = 'The technician was able to verify the concern and the vehicle was operating normally.'
        self.assertFalse(has_error(R(rec), 'does not appear to show it'))


if __name__ == '__main__':
    unittest.main()

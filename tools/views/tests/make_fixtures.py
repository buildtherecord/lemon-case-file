"""Writes tests/fixtures/must_fail/*.json: records the builders must refuse, each with the sentence it must produce (EXPECT.json).

  python3 -m tests.make_fixtures        (from tools/views)

The base record is a small clean one. Every fixture changes exactly one thing, so a failure points at exactly one rule. The test
suite checks that the files on disk match what this script writes."""
import copy, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'fixtures', 'must_fail')


def base():
    return {
        'meta': {'title': 'Fixture record', 'product': 'vehicle', 'summary': 'A technician wrote on a repair order. The owner wrote a letter.', 'ask': 'A review',
                 'updated': 'Oct 3, 2026, 9:00 AM CDT', 'asof': '2026-10-03'},
        'people': [{'id': 'p1', 'name': 'Owner', 'role': 'Claimant'}, {'id': 'p2', 'name': 'Dealer', 'role': 'Service department'}],
        'issues': [{'id': 'noise', 'label': 'Noise'}],
        'exhibits': [
            {'id': 'E1', 'title': 'Repair order', 'date': '2026-02-10', 'kind': 'Repair order', 'author': 'other_side', 'share': True,
             'text': 'Technician was unable to verify the concern. Vehicle not operating normally. Estimate to rebuild: $4,800. The balance remains unpaid in full.'},
            {'id': 'E2', 'title': 'Letter from the owner', 'date': '2026-03-01', 'kind': 'Letter', 'author': 'claimant', 'share': True, 'text': 'We ask for a review.'}],
        'facts': [
            {'id': 'F1', 'date': '2026-02-10', 'text': 'The technician wrote that the vehicle was “not operating normally.”', 'status': 'documented', 'sources': [{'ex': 'E1'}],
             'people': ['p2'], 'issues': ['noise'], 'outward': True},
            {'id': 'F2', 'date': '2026-03-01', 'text': 'The owner wrote a letter asking for a review.', 'status': 'documented', 'sources': [{'ex': 'E2'}], 'people': ['p1'],
             'issues': ['noise'], 'outward': True}],
        'deadlines': []}


def _clipped(r):
    r['exhibits'][1]['text'] = 'Pay the balance unless the vehicle is returned.'
    r['facts'][1]['text'] = 'The owner was told to “Pay the balance” in a letter.'


def _still_unconfirmed(r):
    r['exhibits'] += [{'id': 'R1', 'title': 'Clip', 'date': '2026-02-10', 'kind': 'Video', 'author': 'claimant', 'share': False, 'file': 'R1.mp4'},
                      {'id': 'X1', 'title': 'Still', 'date': '2026-02-10', 'kind': 'Still frame from a recording', 'author': 'claimant', 'share': True, 'feature': True,
                       'caption': 'A frame of the clip', 'excerpt_of': 'R1'}]
    r['facts'].append({'id': 'F3', 'date': '2026-02-10', 'text': 'The clip shows the display going black.', 'status': 'account', 'sources': [{'ex': 'R1'}], 'outward': True,
                       'grade': 'A', 'reviewed_by': 'assistant'})


def _miles_not_in_exhibit(r):
    r['facts'][0]['text'] = 'The repair order shows {miles:E1:48,210:48,222} miles on the odometer.'


def change(f):
    r = base()
    f(r)
    return r


CASES = {
    'advice_wording': (lambda r: r['meta'].update(summary='This is a strong case and you should sue. You will win.'), ['views', 'home'], 'strong case'),
    'quote_drops_not': (lambda r: r['facts'][0]['sources'].__setitem__(0, {'ex': 'E1', 'quote': 'operating normally'}), ['views', 'home'], "cuts off a 'not'"),
    'quote_drops_un': (lambda r: r['facts'][0]['sources'].__setitem__(0, {'ex': 'E1', 'quote': 'able to verify the concern'}), ['views', 'home'], 'not in E1 word for word'),
    'quote_fragment_of_word': (lambda r: r['facts'][0]['sources'].__setitem__(0, {'ex': 'E1', 'quote': 'paid in full'}), ['views', 'home'], 'not in E1 word for word'),
    'quote_changes_dollars': (lambda r: r['facts'][0]['sources'].__setitem__(0, {'ex': 'E1', 'quote': 'Estimate to rebuild: $48.00'}), ['views', 'home'], 'not in E1 word for word'),
    'prose_quote_not_in_source': (lambda r: r['facts'][1].update(text='The owner wrote “we demand a refund.”'), ['views', 'home'], 'are not in'),
    'documented_no_source': (lambda r: r['facts'][1].update(sources=[]), ['views', 'home'], 'names no document'),
    'computed_deadline': (lambda r: r.update(deadlines=[{'label': 'Appeal', 'source': 'The letter', 'date': '2027-03-09', 'computed': True}]), ['views', 'home'], 'never computes'),
    'deadline_without_date_or_words': (lambda r: r.update(deadlines=[{'label': 'Appeal', 'source': 'The letter'}]), ['views', 'home'], "document's own words"),
    'unsafe_id': (lambda r: r['facts'][0].update(id='F1"><img src=x onerror=alert(1)>'), ['views', 'home'], 'not a safe id'),
    'path_id': (lambda r: r['exhibits'][0].update(id='../../escape'), ['views', 'home'], 'not a safe id'),
    'ids_differ_by_capitals': (lambda r: r['exhibits'][1].update(id='e1'), ['views', 'home'], 'differ only by capitals'),
    'script_in_title': (lambda r: r['meta'].update(title='Hello </script><script>alert(1)</script>'), ['views', 'home'], 'page code'),
    'typed_count': (lambda r: r['meta'].update(summary='The car was at the dealer 177 days and returned seven times.'), ['views', 'home'], 'typed into the text'),
    'unknown_placeholder': (lambda r: r['meta'].update(summary='The car had {count:lemons} problems.'), ['views', 'home'], 'not a count this tool knows'),
    'placeholder_unknown_fact': (lambda r: r['meta'].update(summary='That was {days:F1:F99} days later.'), ['views', 'home'], 'not a fact'),
    'beat_title_types_dates': (lambda r: r.update(beats=[{'title': 'March 2026 — The letter', 'from': '2026-03-01', 'to': '2026-03-31'}]), ['views', 'home'], 'types dates'),
    'cites_exhibit_with_range_that_misses': (lambda r: (r['exhibits'][1].update(end='2026-03-10'), r['facts'][1].update(date='2026-08-05')), ['views', 'home'], 'cites E2'),
    'interval_on_month_only_fact': (lambda r: (r['facts'][0].update(date='2026-02', date_precision='month'), r.update(intervals=[{'label': 'Between', 'a': 'F1', 'b': 'F2'}])), ['views', 'home'], 'cannot be computed'),
    'date_not_real': (lambda r: r['facts'][0].update(date='2026-02-30'), ['views', 'home'], 'not a real date'),
    'precision_finer_than_date': (lambda r: r['facts'][0].update(date='2026-02', date_precision='day'), ['views', 'home'], 'only known to the month'),
    'status_not_in_vocabulary': (lambda r: r['facts'][0].update(status='verified'), ['views', 'home'], 'must be one of'),
    'needs_clearance_but_shared': (lambda r: r['exhibits'][0].update(needs_clearance='Counsel'), ['views', 'home'], 'needing clearance'),
    'banned_word_for_this_case': (lambda r: (r['meta'].update(banned=['review']), r['meta'].update(summary='The owner asks for a review.')), ['views', 'home'], 'lists it as a word it never uses'),
    'private_host_link_outward': (lambda r: r['exhibits'][1].update(link='https://records.private.example.com/', feature=True, thumb='https://records.private.example.com/t.jpg', caption='A letter'), ['home'], 'a private site'),
    'counsel_marker_in_summary_outward': (lambda r: r['meta'].update(summary='This summary was compiled for counsel.'), ['home'], 'meant for counsel'),
    'held_phrase_on_page_outward': (lambda r: r['meta'].update(held_phrases=['asks for a review'], summary='The owner asks for a review.'), ['home'], 'holds back'),
    'nothing_released_outward': (lambda r: [f.pop('outward') for f in r['facts']], ['home'], 'would be empty'),
    'dollar_figure_not_in_cited_exhibit': (lambda r: r['facts'][0].update(text='The estimate to rebuild was $48.00.'), ['views', 'home'], 'the figure $48.00'),
    'dollar_figure_far_from_cited_exhibit': (lambda r: r['facts'][0].update(text='The estimate to rebuild was $480,000.'), ['views', 'home'], 'the figure $480,000'),
    'dollar_figure_in_summary_not_in_any_exhibit': (lambda r: r['meta'].update(summary='The estimate to rebuild was $480,000.'), ['views', 'home'], 'any document in the record'),
    'typed_count_repair_orders': (lambda r: r['meta'].update(summary='The dealer wrote nine repair orders.'), ['views', 'home'], "'nine repair orders' is a number typed"),
    'typed_count_stored_faults': (lambda r: r['facts'][1].update(text='The owner listed nineteen stored faults.', status='account', sources=[]), ['views', 'home'], "'nineteen stored faults'"),
    'prognosis_will_likely_win': (lambda r: r['meta'].update(summary='The owner will likely win.'), ['views', 'home'], 'predicts the outcome'),
    'prognosis_good_chance': (lambda r: r['meta'].update(summary='The owners have a good chance.'), ['views', 'home'], 'predicts the outcome'),
    'deadline_asserted': (lambda r: r['meta'].update(summary='The deadline is October 7.'), ['views', 'home'], 'asserts a deadline'),
    'liability_asserted': (lambda r: r['meta'].update(summary='The dealer is liable for the repair.'), ['views', 'home'], 'applies law to the facts'),
    'should_hire_a_lawyer': (lambda r: r['meta'].update(summary='The owner should hire a lawyer.'), ['views', 'home'], 'tells the reader to get legal help'),
    'documented_fact_not_shown_by_document': (lambda r: r['facts'][1].update(text='The dealer replaced the transmission on March 12.'), ['views', 'home'], 'does not appear to show it'),
    'date_in_summary_not_in_record': (lambda r: r['meta'].update(summary='The dealer wrote on March 12, 2027.'), ['views', 'home'], 'no fact, span, document or deadline'),
    'miles_reading_not_in_exhibit': (_miles_not_in_exhibit, ['views', 'home'], 'the reading 48,210 is not in exhibit E1'),
    'clipped_quote_with_strict': (_clipped, ['views', 'home'], "stop right before 'unless'"),
    'future_tense_about_a_past_date_with_strict': (lambda r: r['meta'].update(summary='A review is scheduled for March 1, 2026.'), ['views', 'home'], 'a date before the record'),
    'featured_still_unconfirmed_grade_with_strict': (_still_unconfirmed, ['home'], 'has not confirmed that grade'),
    'unverified_quote_with_strict': (lambda r: r['facts'][1].update(text='The owner wrote “we ask for a review” on paper.', sources=[]), ['views', 'home'], 'cannot be checked'),
}
STRICT_ONLY = {'unverified_quote_with_strict', 'clipped_quote_with_strict', 'future_tense_about_a_past_date_with_strict', 'featured_still_unconfirmed_grade_with_strict'}


def main():
    os.makedirs(OUT, exist_ok=True)
    expect = {}
    for name, (f, tools, contains) in sorted(CASES.items()):
        rec = change(f)
        with open(os.path.join(OUT, name + '.json'), 'w', encoding='utf-8') as fh:
            json.dump(rec, fh, indent=1, ensure_ascii=False)
            fh.write('\n')
        expect[name + '.json'] = {'tools': tools, 'contains': contains, 'args': ['--strict'] if name in STRICT_ONLY else []}
    with open(os.path.join(OUT, 'EXPECT.json'), 'w', encoding='utf-8') as fh:
        json.dump(expect, fh, indent=1)
        fh.write('\n')
    print(f'wrote {len(CASES)} must-fail records to {OUT}')


if __name__ == '__main__':
    main()

"""All 18 persona records and the 3 full records build, under --strict, and come out the way the doctrine says. FULL3 accuses a named person, so it is inward only and its outward build must be refused."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))  # so these run from tests/, tools/views or the repo root
import html, json, os, re, unittest

from tests.helpers import (Base, read, HAVE_PIL, needs_pillow, seeds, seed_record, run, tmpdir, tree, checks, workspace)


INWARD_ONLY = ('FULL3',)


@needs_pillow
class AllRecordsBuild(Base):
    def test_there_are_18_short_records_and_2_full_ones(self):
        _d, ids = seeds()
        self.assertEqual(len(ids), 21)
        self.assertEqual([i for i in ids if i.startswith('FULL')], ['FULL1', 'FULL2', 'FULL3'])

    def test_every_record_builds_in_both_layers_even_strict(self):
        d, ids = seeds()
        out = tmpdir()
        for i in ids:
            with self.subTest(record=i, layer='inward'):
                code, o = run('build_views.py', os.path.join(d, f'{i}.json'), os.path.join(out, f'{i}-in'), '--strict')
                self.assertEqual(code, 0, o)
                self.assertNotIn('Traceback', o)
            with self.subTest(record=i, layer='outward'):
                code, o = run('build_home.py', os.path.join(d, f'{i}.json'), os.path.join(out, f'{i}-out'), '--files-dir', os.path.join(d, f'{i}-files'), '--strict')
                if i in INWARD_ONLY:
                    self.assertNotEqual(code, 0, o)
                    self.assertIn('outward: false', o)
                    self.assertFalse(os.path.exists(os.path.join(out, f'{i}-out', 'index.html')))
                    continue
                self.assertEqual(code, 0, o)
                self.assertNotIn('Traceback', o)
                self.assertTrue(os.path.isfile(os.path.join(out, f'{i}-out', 'index.html')))
                self.assertTrue(os.path.isfile(os.path.join(out, f'{i}-out-private', 'manifest.json')))

    def test_inward_pages_all_carry_the_stamp_the_banner_and_noindex(self):
        d, _ = seeds()
        out = os.path.join(tmpdir(), 'in')
        self.assertEqual(run('build_views.py', os.path.join(d, 'FULL1.json'), out)[0], 0)
        pages = [k for k in tree(out) if k.endswith('.html')]
        self.assertTrue(any(p.startswith('exhibits/') for p in pages) and any(p.startswith('people/') for p in pages) and any(p.startswith('issues/') for p in pages))
        for p in pages:
            t = tree(out)[p].decode()
            with self.subTest(page=p):
                self.has('Last updated', t)
                self.has("Deadlines may apply that you and this page don't know about", html.unescape(t))
                self.has('name="robots" content="noindex,nofollow"', t)

    def test_the_18_persona_pages_are_drafts_and_the_full_record_with_a_finished_gate_is_not(self):
        d, ids = seeds()
        out = tmpdir()
        for i in ids:
            if i in INWARD_ONLY:
                continue
            run('build_home.py', os.path.join(d, f'{i}.json'), os.path.join(out, i), '--files-dir', os.path.join(d, f'{i}-files'))
            page = read(os.path.join(out, i, 'index.html'))
            with self.subTest(record=i):
                if i == 'FULL1':
                    self.lacks('not reviewed for sending', page)
                    self.assertRegex(page, r'Snapshot [0-9a-f]{8}\.')
                else:
                    self.has('DRAFT — not reviewed for sending', page)
                    self.lacks('Snapshot', page)
                self.has('Last updated', page)

    def test_deadlines_in_the_seeds_are_the_letters_own_words_not_letter_plus_180(self):
        for i in ('I1', 'I4'):
            rec = seed_record(i)
            self.assertEqual(len(rec['deadlines']), 1)
            dl = rec['deadlines'][0]
            self.assertNotIn('date', dl)
            self.assertIn('180 days', dl['wording'])
            ex = next(e for e in rec['exhibits'] if e['id'] == dl['ex'])
            self.assertIn(dl['wording'], ex['text'])

    def test_a_record_can_have_several_deadlines_and_none(self):
        self.assertEqual(len(seed_record('FULL1')['deadlines']), 2)
        d, _ = seeds()
        out = os.path.join(tmpdir(), 'in')
        run('build_views.py', os.path.join(d, 'S2.json'), out)
        self.has('That does not mean none applies', tree(out)['index.html'].decode())

    def test_every_exhibit_in_every_record_says_who_wrote_it(self):
        _d, ids = seeds()
        for i in ids:
            for e in seed_record(i)['exhibits']:
                self.assertIn(e.get('author'), ('claimant', 'other_side', 'third_party'), (i, e['id']))

    def test_no_record_types_a_count(self):
        _d, ids = seeds()
        for i in ids:
            rec = seed_record(i)
            for where, text, fact, _v in checks.authored(rec):
                self.assertEqual([x for x in checks.typed_counts(text) if not (fact and x.lower() in ' '.join(
                    e.get('text', '').lower() for e in rec['exhibits']))], [], (i, where))


if __name__ == '__main__':
    unittest.main()

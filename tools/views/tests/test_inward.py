"""The inward pages (build_views.py): links both ways, escaping, labels, counts, dates, and a build that never harms an existing folder."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))  # so these run from tests/, tools/views or the repo root
import html, json, os, unittest

from tests.helpers import Base, needs_pillow, run, tmpdir, tree, workspace, read, leftovers


@needs_pillow
class Inward(Base):
    @classmethod
    def setUpClass(cls):
        cls.w = workspace('FULL1')
        code, o = cls.w.views('--strict')
        assert code == 0, o
        cls.out = os.path.join(cls.w.folder, 'inward')
        cls.t = {k: v.decode() for k, v in tree(cls.out).items()}

    def test_month_only_dates_read_as_the_month_and_are_never_padded(self):
        self.has('September 2025', self.t['chronology.html'])
        self.lacks('Sep 1, 2025', self.t['chronology.html'])

    def test_a_fact_that_only_the_claimants_documents_support_says_whose(self):
        text = html.unescape(self.t['chronology.html'])
        self.has("Per the owner's letter of Oct 2, 2025", text)
        self.has('Shows in a document', text)

    def test_an_open_item_is_labelled_open_and_counted_apart(self):
        self.has('Open question, not stated as fact', self.t['chronology.html'])
        self.assertEqual(json.loads(self.t['counts.json'])['open'], 1)

    def test_excerpts_and_duplicates_sit_under_their_parent_and_are_not_counted(self):
        c = self.t['chronology.html']
        self.assertLess(c.index('id="F8"'), c.index('id="F9"'))
        self.has('Excerpt of', c)
        self.has('folded, not counted', c)
        counts = json.loads(self.t['counts.json'])
        self.assertEqual(counts['facts'], 13)   # 15 facts - 1 excerpt - 1 folded duplicate
        self.assertEqual(counts['exhibits'], 9)  # 11 exhibits - 1 excerpt - 1 folded duplicate

    def test_numbers_in_the_brief_are_filled_in_from_the_record(self):
        idx = self.t['index.html']
        self.has('This page holds 13 dated entries and 8 documents.', idx)
        self.has('148 days', idx)
        self.has('computed', idx)

    def test_deadlines_show_the_documents_words(self):
        text = html.unescape(self.t['index.html'])
        self.has('the document says: “within 30 days”', text)
        self.has('Example Attorney', text)
        self.has('nobody yet', text)

    def test_gaps_page_reports_checked_and_unchecked_quotes(self):
        self.has('quotes were checked word for word and matched', self.t['gaps.html'])

    def test_exhibit_pages_say_whether_they_are_on_the_outward_page(self):
        self.has('On the outward page', self.t['exhibits/E1.html'])
        self.has('Not on the outward page', self.t['exhibits/E6.html'])

    def test_text_is_escaped_not_run(self):
        w = workspace('FULL1')
        w.fact('F2')['text'] = 'The dealer wrote <b>bold</b> from <sam@x.co> & more.'
        w.fact('F2')['sources'] = []
        w.fact('F2')['status'] = 'account'
        code, o = w.views()
        self.assertEqual(code, 0, o)
        t = w.page('chronology.html', os.path.join(w.folder, 'inward'))
        self.has('&lt;b&gt;bold&lt;/b&gt; from &lt;sam@x.co&gt; &amp; more.', t)
        self.lacks('<b>bold</b>', t)

    def test_odd_but_safe_ids_and_file_names_become_safe_links(self):
        w = workspace('FULL1')
        w.exhibit('E1')['file'] = 'my doc #1 & more.pdf'
        code, o = w.views()
        self.assertEqual(code, 0, o)
        self.has('../files/my%20doc%20%231%20%26%20more.pdf', w.page('exhibits/E1.html', os.path.join(w.folder, 'inward')))


class OutputFolders(Base):
    def record(self):
        from tests import make_fixtures
        d = tmpdir()
        path = os.path.join(d, 'r.json')
        with open(path, 'w') as fh:
            json.dump(make_fixtures.base(), fh)
        return d, path

    def test_a_folder_the_tool_did_not_make_is_refused_and_left_alone(self):
        d, path = self.record()
        out = os.path.join(d, 'important')
        os.makedirs(os.path.join(out, 'sub'))
        with open(os.path.join(out, 'sub', 'notes.txt'), 'w') as fh:
            fh.write('mine')
        for tool in ('build_views.py', 'build_home.py'):
            code, o = run(tool, path, out)
            self.assertEqual(code, 1, o)
            self.has('did not make', o)
            self.assertEqual(read(os.path.join(out, 'sub', 'notes.txt')), 'mine')
            self.assertEqual(os.listdir(out), ['sub'])
        self.assertEqual(leftovers(d), [])

    def test_an_empty_folder_is_fine_and_a_made_folder_is_replaced(self):
        d, path = self.record()
        out = os.path.join(d, 'out')
        os.makedirs(out)
        self.assertEqual(run('build_views.py', path, out)[0], 0)
        first = tree(out)
        self.assertIn('.btr-output', first)
        with open(os.path.join(out, 'stray.txt'), 'w') as fh:
            fh.write('generated folder content is replaced')
        self.assertEqual(run('build_views.py', path, out)[0], 0)
        self.assertEqual(tree(out), first)
        self.assertEqual(leftovers(d), [])

    def test_a_failed_build_leaves_the_old_folder_exactly_as_it_was(self):
        d, path = self.record()
        out = os.path.join(d, 'out')
        self.assertEqual(run('build_views.py', path, out)[0], 0)
        before = tree(out)
        with open(path) as fh:
            rec = json.load(fh)
        rec['meta']['summary'] = 'This is a strong case.'
        with open(path, 'w') as fh:
            json.dump(rec, fh)
        code, o = run('build_views.py', path, out)
        self.assertEqual(code, 1)
        self.assertEqual(tree(out), before)
        self.assertEqual(leftovers(d), [])

    def test_a_bad_command_line_says_what_is_wrong(self):
        d, path = self.record()
        code, o = run('build_home.py', path, os.path.join(d, 'o'), '--files-dir', os.path.join(d, 'nope'))
        self.assertEqual(code, 1)
        self.has('does not exist', o)
        code, o = run('build_views.py', os.path.join(d, 'missing.json'), os.path.join(d, 'o'))
        self.assertEqual(code, 1)
        self.has('was not found', o)
        with open(os.path.join(d, 'broken.json'), 'w') as fh:
            fh.write('{"meta": ')
        code, o = run('build_views.py', os.path.join(d, 'broken.json'), os.path.join(d, 'o'))
        self.assertEqual(code, 1)
        self.has('not valid JSON', o)
        self.lacks('Traceback', o)

    def test_the_checker_command_works_on_its_own(self):
        d, path = self.record()
        code, o = run('checks.py', path)
        self.assertEqual(code, 0, o)
        self.has('record checks passed', o)


if __name__ == '__main__':
    unittest.main()

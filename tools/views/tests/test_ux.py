"""The outward page on a phone and for keyboard readers: contrast, the day-counting rule, marks, jump links, print, and the viewer layout."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))  # so these run from tests/, tools/views or the repo root
import datetime as dt, json, os, re, shutil, subprocess, unittest

from tests.helpers import Base, VIEWS, needs_pillow, workspace
import build_home

NODE = shutil.which('node')
needs_node = unittest.skipUnless(NODE, 'node is not installed')


def lum(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def tokens(css, dark):
    m = re.search(r'@media \(prefers-color-scheme:dark\)\{:root\{([^}]*)\}', css) if dark else re.search(r':root\{([^}]*)\}', css)
    t = dict(x.split(':') for x in m.group(1).split(';') if x)
    if dark:
        t = {**tokens(css, False), **{k: v for k, v in t.items()}}
    return {k.lstrip('-'): v for k, v in t.items()}


def js(code):
    r = subprocess.run([NODE, '-e', f'const m=require({json.dumps(os.path.join(VIEWS, "cursor.js"))});{code}'], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


class Base(Base):
    def rx(self, pattern, text, note=''):
        if not re.search(pattern, text):
            self.fail(f'expected the pattern {pattern!r} but it is not there. {note}')


class Contrast(Base):
    def test_text_colours_pass_AA_in_both_schemes(self):
        for dark in (False, True):
            t = tokens(build_home.CSS, dark)
            for fg in ('muted', 'amber', 'link', 'hot', 'blue', 'ink'):
                for bg in ('bg', 'card'):
                    self.assertGreaterEqual(ratio(t[fg], t[bg]), 4.5, f'{fg} on {bg} {"dark" if dark else "light"}: {ratio(t[fg], t[bg]):.2f}')

    def test_marks_and_cursor_pass_the_non_text_minimum(self):
        for dark in (False, True):
            t = tokens(build_home.CSS, dark)
            for bg in ('bg', 'card'):
                self.assertGreaterEqual(ratio(t['mk'], t[bg]), 3, 'mark fill')
                self.assertGreaterEqual(ratio(t['cursor'], t[bg]), 3, f'red cursor {"dark" if dark else "light"}')
            self.assertGreaterEqual(ratio(t['onmk'], t['mk']), 4.5, 'the count inside a mark')

    def test_dark_cursor_is_brighter_than_the_light_one(self):
        self.assertNotEqual(tokens(build_home.CSS, True)['cursor'], tokens(build_home.CSS, False)['cursor'])

    def test_no_caption_fade_and_links_are_underlined_in_the_text_colour(self):
        css = build_home.CSS
        self.assertIsNone(re.search(r'\.media small\{[^}]*opacity', css))
        self.has('text-decoration-color:currentColor', css)


class DayCounting(Base):
    SPANS = [('2026-06-11', '2026-09-28'), ('2024-09-16', '2025-03-12'), ('2025-02-27', '2025-03-01'), ('2024-02-28', '2024-03-01'), ('2025-05-05', '2025-05-05')]

    def test_python_and_javascript_agree_and_the_end_date_is_day_M_of_M(self):
        if not NODE:
            self.skipTest('node is not installed')
        for s, e in self.SPANS:
            t = [dt.date.fromisoformat(s) + dt.timedelta(days=i) for i in range((dt.date.fromisoformat(e) - dt.date.fromisoformat(s)).days + 1)]
            out = js(f'''const p=d=>Date.parse(d);const s=p({json.dumps(s)}),e=p({json.dumps(e)});
              console.log(JSON.stringify({{M:m.spanTotal(s,e),days:{json.dumps([x.isoformat() for x in t])}.map(d=>m.spanDay(s,p(d)))}}))''')
            M = build_home.span_days(s, e)
            self.assertEqual(out['M'], M, (s, e))
            self.assertEqual(out['days'][-1], M, f'the end date must read day {M} of {M}')
            self.assertEqual(out['days'][0], 0)
            self.assertTrue(all(0 <= d <= M for d in out['days']), 'day N must never exceed M')

    def test_the_label_on_the_page_is_the_same_number_the_cursor_ends_on(self):
        if not NODE:
            self.skipTest('node is not installed')
        w = workspace('FULL1')
        self.assertEqual(w.home()[0], 0)
        page = w.page()
        data = json.loads(re.search(r'<script type="application/json" id="swdata">(.*?)</script>', page, re.S).group(1))
        self.assertTrue(data['spans'])
        for sp in data['spans']:
            labels = set(re.findall(re.escape(sp['label']) + r' · (\d+) days?', page))
            self.assertEqual(len(labels), 1, labels)
            out = js(f'''const p=d=>Date.parse(d);console.log(JSON.stringify([m.spanTotal(p({json.dumps(sp["s"])}),p({json.dumps(sp["e"])})),m.spanDay(p({json.dumps(sp["s"])}),p({json.dumps(sp["e"])}))]))''')
            self.assertEqual(out[0], out[1])
            self.assertEqual(str(out[0]), labels.pop())

    @needs_node
    def test_cut_text_ends_at_a_word_and_never_gains_quotation_marks(self):
        out = js('''console.log(JSON.stringify([m.cutWords("Hand pulls a door window switch while the vehicle is moving; the display shows a warning", 40), m.cutWords("short text", 40), m.cutWords("Averyveryverylongwordwithoutanyspaces and more", 20)]))''')
        for cut in out:
            self.assertIsNone(re.search(r'[“”"]', cut))
        self.assertEqual(out[0], 'Hand pulls a door window switch while …')
        self.assertEqual(out[1], 'short text')
        self.assertTrue(out[2].endswith('…'))


@needs_pillow
class Page(Base):
    @classmethod
    def setUpClass(cls):
        cls.w = workspace('FULL1')
        assert cls.w.home()[0] == 0
        cls.page = cls.w.page()

    def test_first_screen_order_and_wording(self):
        p = self.page
        i = lambda s: p.index(s)
        self.assertLess(i('Last updated'), i('class="jump"'))
        self.assertLess(i('class="jump"'), i('class="brief"'))
        self.has('<strong>', p[i('class="brief"'):i('class="tiles"')])
        self.assertNotIn('dated entries on this page', p)
        self.assertNotIn('shared here', p)
        self.assertGreater(i('Snapshot '), i('<footer'), 'the snapshot line belongs in the footer')

    def test_jump_links_with_counts_land_on_real_ids(self):
        p = self.page
        nav = re.search(r'<nav class="jump".*?</nav>', p, re.S).group(0)
        targets = re.findall(r'href="#([^"]+)"', nav)
        self.assertGreaterEqual(len(targets), 4)
        for t in targets:
            self.has(f'id="{t}"', p)
        self.rx(r'All entries <span>11</span>', nav)

    def test_every_id_is_used_once_and_beat_copies_have_their_own(self):
        ids = re.findall(r'\sid="([^"]+)"', self.page)
        self.assertEqual(len(ids), len(set(ids)))
        self.has('id="e-F3"', self.page)
        self.has('id="b1-F3"', self.page)

    def test_timeline_marks_all_link_to_the_canonical_entry_and_say_their_status(self):
        for m in re.finditer(r'<a class="mk" href="#(e-[^"]+)" data-ids="([^"]+)" data-d="[^"]+"><title>([^<]*)</title>', self.page):
            self.has(f'id="{m.group(1)}"', self.page)
            self.rx(r"Shows in a document|Claimant|Disputed|Open question|Per the|entries \(", m.group(3))

    def test_same_lane_same_day_entries_make_one_mark_with_a_count(self):
        self.has('data-ids="F6 F7"', self.page)
        self.rx(r'<text class="mn(?: r)?" [^>]*>2</text>', self.page)

    def test_disputed_has_its_own_shape_and_the_legend_lists_only_what_is_present(self):
        self.has('<path class="m m-disputed"', self.page)
        legend = re.search(r'<div class="legend">.*?</div>', self.page, re.S).group(0)
        self.has('disputed', legend)
        w = workspace('FULL1')
        for f in w.rec['facts']:
            if f['status'] in ('disputed', 'open'):
                f['status'] = 'account'
        self.assertEqual(w.home()[0], 0)
        legend2 = re.search(r'<div class="legend">.*?</div>', w.page(), re.S).group(0)
        self.assertNotIn('disputed', legend2)
        self.assertNotIn('open question', legend2)
        self.assertNotIn('m-disputed', w.page().split('<style>')[1].split('</style>')[1])

    def test_the_axis_always_shows_the_year_and_the_as_of_line_is_drawn(self):
        self.rx(r'<text class="yr"[^>]*>2025</text>', self.page)
        self.has('as of Nov 5, 2025', self.page)
        self.has('class="asof"', self.page)

    def test_axis_year_for_a_short_case(self):
        w = workspace('FULL1')
        w.rec['facts'] = [f for f in w.rec['facts'] if f['date'] >= '2025-10-02' and f['date'] < '2025-10-25' and not f.get('fold_into')]
        w.rec['intervals'] = []
        w.rec['beats'] = []
        w.rec['spans'] = []
        w.rec['meta']['summary'] = 'A letter and a reply.'
        w.rec['meta'].pop('review_opened', None)
        code, o = w.home()
        self.assertEqual(code, 0, o)
        self.rx(r'<text class="yr"[^>]*>2025</text>', w.page())
        self.rx(r'<text class="tl"[^>]*>Oct \d+</text>', w.page())    # weekly ticks for a case under 60 days

    def test_only_a_recording_that_can_be_played_gets_the_play_icon(self):
        p = self.page
        strip = p[p.index('class="media"'):p.index('</div>', p.index('class="media"'))]
        playable = [m for m in re.findall(r'<a [^>]*data-lbid="[^"]+"[^>]*>', strip)]
        self.assertEqual([('E8' in a, 'class=pl' in a) for a in playable], [(False, False), (True, True)])
        self.has('"type": "video"', p.replace('"type":"video"', '"type": "video"'))

    def test_a_recording_with_no_file_here_is_not_playable(self):
        w = workspace('FULL1')
        w.exhibit('E8')['file'] = w.exhibit('E8')['file'].replace('.mp4', '.png')
        shutil.copy(os.path.join(w.files, 'E7.jpg'), os.path.join(w.files, 'E8.png'))
        self.assertEqual(w.home()[0], 0)
        self.assertNotIn('class=pl', w.page())

    def test_the_strip_heading_is_computed_from_what_it_holds(self):
        self.has('Key documents and recordings', self.page)
        w = workspace('FULL1')
        w.exhibit('E8')['feature'] = False
        self.assertEqual(w.home()[0], 0)
        self.has('Key documents <span', w.page())
        self.assertNotIn('Key documents and recordings', w.page())

    def test_reading_strip_skip_link_and_live_region_are_present(self):
        p = self.page
        self.has('href="#s-parts">Skip the timeline</a>', p)
        self.has('id="swstrip" hidden', p)
        self.has('"aria-live", "polite"', p)
        self.has('id="swhelp" hidden', p)
        self.assertNotIn('aria-describedby="swhelp"', p.split('<script>')[0], 'the help text is attached by the script, because it describes keys that only work with it')
        self.assertEqual(p.count('class="sv sv-'), 3)

    def test_print_opens_every_section(self):
        self.has('@media print', self.page)
        self.has('beforeprint', self.page)

    def test_viewer_has_a_bottom_bar_and_sits_outside_main(self):
        p = self.page
        self.has('<div class="bot">', p)
        self.assertGreater(p.index('<div id="lb"'), p.index('</main>'))
        self.has('aria-labelledby="lbt"', p)
        self.has('min-height:44px', p.split('#lb button')[1][:200])

    def test_nothing_from_the_viewer_or_timeline_text_trips_the_outward_checks(self):
        self.assertNotIn('Snapshot', build_home.CSS)
        w = workspace('FULL1')
        w.rec['meta'].pop('share_gate')
        self.assertEqual(w.home()[0], 0)
        self.assertNotIn('Snapshot', w.page())


@needs_pillow
class Inward(Base):
    def test_exhibits_table_becomes_cards_and_the_nav_is_padded_and_marked(self):
        w = workspace('FULL1')
        self.assertEqual(w.views()[0], 0)
        inward = os.path.join(w.folder, 'inward')
        ex = w.page('exhibits.html', inward)
        self.has('<table class="cards">', ex)
        self.has('data-l="Cited by"', ex)
        self.has('<a href="exhibits.html" aria-current=page>Exhibits</a>', ex)
        self.has('nav a{display:inline-block;padding:13px 6px}', ex)
        self.has('<a href="index.html" aria-current=page>Brief</a>', w.page('index.html', inward))
        self.assertNotIn('<br><small class="muted"><a', w.page('index.html', inward))


if __name__ == '__main__':
    unittest.main()

"""The outward page (build_home.py): release is opt-in, files are scrubbed, the private report stays outside, the snapshot covers every file."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))  # so these run from tests/, tools/views or the repo root
import hashlib, html, json, os, shutil, unittest

from tests.helpers import (Base, needs_pillow, needs_pdf_tools, needs_ffmpeg, run, tmpdir, tree, workspace, read, leftovers, HAVE_FFMPEG)

GATE = {'recipient': 'Example recipient', 'confidentiality_checked': True, 'names_checked': True, 'defamation_reminder_ack': True, 'attorney_read': True}


def sha(b):
    return hashlib.sha256(b).hexdigest()


@needs_pillow
class Release(Base):
    def test_nothing_is_released_by_default(self):
        w = workspace('FULL1')
        w.exhibit('E2').pop('share')
        w.fact('F7').pop('outward')
        code, o = w.home()
        self.assertEqual(code, 0, o)
        self.assertNotIn('files/E2.png', tree(w.out))
        page = w.page()
        self.lacks('id="e-F7"', page)
        self.has('NOT SHARED E2', w.report())
        self.has('no share decision recorded', w.report())
        self.has('NOT RELEASED F7', w.report())
        self.has('no outward decision recorded', w.report())

    def test_a_number_computed_from_an_unreleased_fact_is_refused(self):
        w = workspace('FULL1')
        w.fact('F2').pop('outward')       # the first section's text computes days from F2's date
        code, o = w.home()
        self.assertEqual(code, 1)
        self.has('would leak through the number', o)

    def test_the_video_exception_is_gone(self):
        w = workspace('FULL1')
        w.exhibit('E8')['share'] = False
        code, o = w.home()
        self.assertEqual(code, 0, o)
        t = tree(w.out)
        self.assertFalse([k for k in t if 'E8' in k], 'an unshared recording and its thumbnail must not be copied')
        page = w.page()
        self.lacks('E8.mp4', page)
        self.lacks('thumbs/E8', page)
        self.lacks('data-lbid="E8"', page)

    def test_unshared_documents_are_not_copied_and_get_no_page_images(self):
        w = workspace('FULL1')
        self.assertEqual(w.home()[0], 0)
        t = tree(w.out)
        for gone in ('E6', 'E10', 'E11'):
            self.assertFalse([k for k in t if gone + '.' in k or gone + '-' in k], gone)
        self.has('(document not included here)', w.page())

    def test_an_unshared_exhibit_is_never_linked_copied_or_listed(self):
        w = workspace('FULL1')
        w.exhibit('E4')['share'] = False          # a cited PDF with page images
        code, o = w.home()
        self.assertEqual(code, 0, o)
        t = tree(w.out)
        self.assertFalse([k for k in t if 'E4' in k], 'no file and no page image of an unshared PDF')
        page = w.page()
        self.lacks('E4.pdf', page)
        self.lacks('#x-E4', page)
        self.lacks('"id": "E4"', page.replace('"id":"E4"', '"id": "E4"'))
        self.lacks('Owner\'s letter to the manufacturer', html.unescape(page))
        self.has('(document not included here)', page)
        self.has('NOT SHARED E4', w.report())

    def test_a_quote_that_comes_only_from_an_unshared_document_is_noted(self):
        w = workspace('FULL1')
        w.exhibit('E5')['share'] = False
        code, o = w.home()
        self.assertEqual(code, 0, o)
        self.has('appear only in E5, which is not shared', w.report())

    def test_a_shared_document_nobody_cites_is_not_copied(self):
        w = workspace('FULL1')
        w.rec['exhibits'].append({'id': 'E12', 'title': 'Unused', 'date': '2025-03-01', 'kind': 'Photo index', 'author': 'claimant', 'share': True, 'file': 'E12.png'})
        shutil.copyfile(os.path.join(w.files, 'E2.png'), os.path.join(w.files, 'E12.png'))
        code, o = w.home()
        self.assertEqual(code, 0, o)
        self.assertNotIn('files/E12.png', tree(w.out))
        self.has('E12', w.report())

    def test_the_report_and_manifest_live_outside_the_published_folder(self):
        w = workspace('FULL1')
        self.assertEqual(w.home()[0], 0)
        published, private = tree(w.out), tree(w.private)
        for name in ('share-report.txt', 'manifest.json', 'snapshot.json'):
            self.assertIn(name, private)
            self.assertNotIn(name, published)
        self.assertEqual(set(published), {r['path'] for r in w.manifest()['files']})
        for r in w.manifest()['files']:
            self.assertEqual(r['sha256'], sha(published[r['path']]), r['path'])

    def test_nothing_in_the_published_folder_points_at_a_private_site_or_holds_a_record(self):
        w = workspace('FULL1')
        self.assertEqual(w.home()[0], 0)
        for k, v in tree(w.out).items():
            self.assertFalse(k.endswith('.json'), k)
            if k.endswith(('.html', '.txt')):
                self.lacks('private.example.com', v.decode())

    def test_a_link_or_thumb_on_a_private_site_stops_the_build(self):
        w = workspace('FULL1')
        w.exhibit('E7')['thumb'] = 'https://records.private.example.com/t.jpg'
        code, o = w.home()
        self.assertEqual(code, 1)
        self.has('a private site', o)

    def test_unfinished_share_gate_means_a_draft_with_no_snapshot_id(self):
        for missing in list(GATE) + [None]:
            w = workspace('FULL1')
            gate = dict(GATE)
            if missing:
                gate[missing] = '' if missing == 'recipient' else False
            w.rec['meta']['share_gate'] = gate
            code, o = w.home()
            self.assertEqual(code, 0, o)
            page = w.page()
            with self.subTest(missing=missing):
                if missing:
                    self.has('DRAFT — not reviewed for sending', page)
                    self.lacks('Snapshot', page)
                    self.assertIsNone(w.manifest()['snapshot'])
                    self.assertEqual(w.manifest()['share_gate_missing'], [missing])
                    self.has('DRAFT', html.unescape(page[page.index('<title>'):page.index('</title>')]))
                else:
                    self.lacks('not reviewed for sending', page)
                    snap = w.manifest()['snapshot']
                    self.assertRegex(snap, r'^[0-9a-f]{8}$')
                    self.has(f'Snapshot {snap}.', page)

    def test_no_share_gate_at_all_is_a_draft(self):
        w = workspace('FULL1')
        w.rec['meta'].pop('share_gate')
        self.assertEqual(w.home()[0], 0)
        self.has('DRAFT — not reviewed for sending', w.page())

    def test_page_text_checks(self):
        w = workspace('FULL1')
        self.assertEqual(w.home()[0], 0)
        page = html.unescape(w.page())
        self.has('Last updated', page)
        self.has('Per the owner\'s letter of Oct 2, 2025', page)       # only the claimant's own document supports it
        self.has('Open question, not stated as fact', page)          # an open item never reads as fact
        self.has('September 2025', page)                              # month-only date, not Sep 1
        self.lacks('Sep 1, 2025', page)
        self.has('Excerpt of F8', page)
        self.lacks('Second copy of the repair order', page)          # folded duplicate is hidden
        self.lacks('considering a letter to the state agency', page)   # held back
        self.lacks('Manufacturer follow-up', page)                    # deadlines never render outward
        self.lacks('Example Attorney', page)                          # nor the lawyer field or who confirmed
        self.has('This page holds 11 dated entries and 6 documents.', page)   # computed, excerpts and folds left out

    def test_section_dates_are_printed_from_the_sections_own_range(self):
        w = workspace('FULL1')
        self.assertEqual(w.home()[0], 0)
        page = w.page()
        self.has('February to April 2025', page)
        self.has('September 2025 — The display unit was replaced.', html.unescape(page))


@needs_pillow
class Snapshot(Base):
    def test_same_inputs_same_snapshot(self):
        w = workspace('FULL1')
        self.assertEqual(w.home()[0], 0)
        a = w.manifest()['snapshot']
        self.assertEqual(w.home()[0], 0)
        self.assertEqual(w.manifest()['snapshot'], a)

    def test_changing_a_shared_file_changes_the_snapshot(self):
        w = workspace('FULL1')
        self.assertEqual(w.home()[0], 0)
        a = w.manifest()['snapshot']
        from PIL import Image
        Image.new('RGB', (100, 80), 'red').save(os.path.join(w.files, 'E2.png'))
        self.assertEqual(w.home()[0], 0)
        self.assertNotEqual(w.manifest()['snapshot'], a, 're-masking a document must change the id')

    def test_changing_a_thumbnail_or_the_page_changes_it_too(self):
        w = workspace('FULL1')
        self.assertEqual(w.home()[0], 0)
        a = w.manifest()['snapshot']
        from PIL import Image
        Image.new('RGB', (100, 80), 'blue').save(os.path.join(w.files, 'thumbs', 'E7.jpg'))
        self.assertEqual(w.home()[0], 0)
        b = w.manifest()['snapshot']
        self.assertNotEqual(b, a)
        w.fact('F2')['text'] = 'First visit: the dealer wrote “unable to duplicate” for a display that goes black at night.'
        self.assertEqual(w.home()[0], 0)
        self.assertNotEqual(w.manifest()['snapshot'], b)

    def test_the_rule_can_be_checked_by_hand(self):
        w = workspace('FULL1')
        self.assertEqual(w.home()[0], 0)
        m, t = w.manifest(), tree(w.out)
        page = t['index.html'].decode().replace(m['snapshot'], 'SNAPSHOT-ID')
        lines = []
        for r in m['files']:
            h = hashlib.sha256(page.encode()).hexdigest() if r['path'] == 'index.html' else sha(t[r['path']])
            lines.append(f"{r['path']}\t{h}")
        self.assertEqual(hashlib.sha256(('\n'.join(sorted(lines)) + '\n').encode()).hexdigest(), m['content_sha256'])
        self.assertEqual(m['content_sha256'][:8], m['snapshot'])

    def test_archive_keeps_a_dated_copy_with_the_recipient_and_never_overwrites(self):
        w = workspace('FULL1')
        sent = os.path.join(w.folder, 'sent')
        code, o = w.home('--archive', sent)
        self.assertEqual(code, 0, o)
        made = os.listdir(sent)
        self.assertEqual(len(made), 1)
        dest = os.path.join(sent, made[0])
        self.assertTrue(made[0].endswith(w.manifest()['snapshot']))
        self.assertEqual(json.loads(read(os.path.join(dest, 'sent.json')))['recipient'], GATE['recipient'].replace('Example recipient', 'Example Manufacturer, customer care (fictional)'))
        self.assertEqual(tree(os.path.join(dest, 'published')).keys(), tree(w.out).keys())
        self.assertIn('manifest.json', tree(os.path.join(dest, 'private')))
        code, o = w.home('--archive', sent)
        self.assertEqual(code, 0, o)
        self.has('already holds this exact copy', o)
        self.assertEqual(os.listdir(sent), made)

    def test_a_draft_cannot_be_archived(self):
        w = workspace('FULL1')
        w.rec['meta']['share_gate']['attorney_read'] = False
        code, o = w.home('--archive', os.path.join(w.folder, 'sent'))
        self.assertEqual(code, 1)
        self.has('A draft is not a sent copy', o)
        self.assertFalse(os.path.exists(os.path.join(w.folder, 'sent')))


@needs_pillow
class WhatGoesOut(Base):
    def test_text_markers_stop_the_build(self):
        for words in ('Compiled for counsel.', 'This memo is privileged.', 'Attorney work product.', 'A Rule 408 settlement offer.'):
            w = workspace('FULL1')
            with open(os.path.join(w.files, 'E5.html'), 'w') as fh:
                fh.write(f'<html><body><p>{words}</p></body></html>')
            code, o = w.home()
            with self.subTest(words=words):
                self.assertEqual(code, 1, o)
                self.has('meant for counsel', o)
                self.has('E5.html', o)
                self.assertFalse(os.path.exists(w.out))

    def test_the_other_sides_own_boilerplate_can_be_allowed_by_name_and_is_listed(self):
        w = workspace('FULL2')
        w.rec['meta']['share_gate'] = dict(GATE)
        code, o = w.home()
        self.assertEqual(code, 0, o)
        self.has("allowed by allow_markers on exhibit E3", w.report())
        w.exhibit('E3').pop('allow_markers')
        self.assertEqual(w.home()[0], 1)

    def test_a_held_phrase_in_an_outgoing_file_stops_the_build(self):
        w = workspace('FULL2')
        with open(os.path.join(w.files, 'E3.html'), 'w') as fh:
            fh.write('<html><body><p>Our preservation demand is planned.</p></body></html>')
        code, o = w.home()
        self.assertEqual(code, 1, o)
        self.has('holds back', o)

    def test_a_marker_in_a_document_that_is_not_shared_does_not_matter(self):
        w = workspace('FULL2')
        self.assertEqual(w.home()[0], 0)   # E4 is a memo for counsel and is not shared
        self.assertNotIn('files/E4.pdf', tree(w.out))

    def test_personal_details_are_listed_for_you_to_clear_not_blocked(self):
        w = workspace('FULL1')
        with open(os.path.join(w.files, 'E5.html'), 'w') as fh:
            fh.write('<html><body><p>Call 312-555-0142 or write sam@example.com at 12 Main Street, Springfield IL 62704. Account 123456789012.</p></body></html>')
        code, o = w.home()
        self.assertEqual(code, 0, o)
        r = w.report()
        for part in ('email address: sam@example.com', 'phone number: 312-555-0142', 'street address: 12 Main Street', 'state and ZIP code: IL 62704', 'long number'):
            self.has(part, r)

    def test_html_exhibits_get_noindex(self):
        w = workspace('FULL1')
        self.assertEqual(w.home()[0], 0)
        self.has('name="robots" content="noindex,nofollow"', w.page('files/E5.html'))

    def test_files_in_subfolders_and_odd_names_work(self):
        w = workspace('FULL1')
        os.makedirs(os.path.join(w.files, 'sub', 'dir'))
        shutil.move(os.path.join(w.files, 'E2.png'), os.path.join(w.files, 'sub', 'dir', 'my doc #1.png'))
        w.exhibit('E2')['file'] = 'sub/dir/my doc #1.png'
        code, o = w.home()
        self.assertEqual(code, 0, o)
        self.assertIn('files/sub/dir/my doc #1.png', tree(w.out))
        self.has('files/sub/dir/my%20doc%20%231.png', w.page())

    def test_two_file_names_that_differ_only_by_capitals_are_refused(self):
        # a Mac cannot hold both files at once, so the rule is checked where the build records what it will publish
        import build_home
        from tests.helpers import checks, seeds
        d, _ = seeds()
        n, R = checks.check_record(json.loads(read(os.path.join(d, 'FULL1.json'))), 'outward', False, os.path.join(d, 'FULL1-files'))
        ow = build_home.Outward(n, R, os.path.join(d, 'FULL1-files'))
        self.assertTrue(ow.register('files/a.png', 'x', 'E1', ''))
        self.assertFalse(ow.register('files/A.png', 'y', 'E2', ''))
        self.assertTrue(any('differ only by capitals' in e for e in R.errors))

    def test_a_missing_or_escaping_file_is_a_sentence(self):
        w = workspace('FULL1')
        os.remove(os.path.join(w.files, 'E2.png'))
        code, o = w.home()
        self.assertEqual(code, 1)
        self.has('E2 is shared, but its file', o)
        self.assertFalse(os.path.exists(w.out))
        w = workspace('FULL1')
        w.exhibit('E2')['file'] = '../E2.png'
        code, o = w.home()
        self.assertEqual(code, 1)
        self.has('must be a path inside the files folder', o)

    def test_a_corrupt_pdf_or_picture_is_a_sentence_naming_the_exhibit(self):
        w = workspace('FULL1')
        with open(os.path.join(w.files, 'E1.pdf'), 'wb') as fh:
            fh.write(b'not a pdf at all')
        with open(os.path.join(w.files, 'E2.png'), 'wb') as fh:
            fh.write(b'not a picture either')
        code, o = w.home()
        self.assertEqual(code, 1)
        self.has("exhibit E1 (file): 'E1.pdf' could not be read as a PDF", o)
        self.has("exhibit E2 (file): The image 'E2.png' could not be rewritten", o)
        self.lacks('Traceback', o)
        self.assertFalse(os.path.exists(w.out))

    def test_a_file_type_that_cannot_be_scrubbed_is_refused_by_name(self):
        w = workspace('FULL1')
        shutil.copyfile(os.path.join(w.files, 'E2.png'), os.path.join(w.files, 'E2.docx'))
        w.exhibit('E2')['file'] = 'E2.docx'
        code, o = w.home()
        self.assertEqual(code, 1)
        self.has('exhibit E2', o)
        self.has('cannot scrub', o)

    def test_the_output_folder_may_not_overlap_the_files_folder_or_the_report(self):
        w = workspace('FULL1')
        code, o = w.home(out=os.path.join(w.files, 'out'))
        self.assertEqual(code, 1)
        self.has('overlaps the files folder', o)
        code, o = w.home('--private-dir', os.path.join(w.out, 'private'))
        self.assertEqual(code, 1)
        self.has('different folder', o)

    def test_featured_recording_needs_the_owners_grade_under_strict(self):
        w = workspace('FULL1')
        w.fact('F8')['reviewed_by'] = 'assistant'
        code, o = w.home()
        self.assertEqual(code, 0, o)
        self.has('grade A set by the owner', o)
        code, o = w.home('--strict', out=os.path.join(w.folder, 'out2'))
        self.assertEqual(code, 1)
        self.has('grade A set by the owner', o)

    def test_featured_items_need_a_public_caption_under_strict(self):
        w = workspace('FULL1')
        w.exhibit('E7').pop('caption')
        self.assertEqual(w.home()[0], 0)
        code, o = w.home('--strict', out=os.path.join(w.folder, 'out2'))
        self.assertEqual(code, 1)
        self.has('no public caption', o)

    def test_no_temp_folders_are_left_behind(self):
        w = workspace('FULL1')
        w.home()
        w.rec['meta']['summary'] = 'This is a strong case.'
        w.home()
        self.assertEqual(leftovers(w.folder), [])


@needs_pdf_tools
class PdfPages(Base):
    def test_pages_are_made_only_for_shared_pdfs_and_named_by_id(self):
        w = workspace('FULL1')
        self.assertEqual(w.home()[0], 0)
        pages = sorted(k for k in tree(w.out) if k.startswith('files/pages/'))
        self.assertEqual(pages, ['files/pages/E1-1.jpg', 'files/pages/E1-2.jpg', 'files/pages/E4-1.jpg', 'files/pages/E4-2.jpg'])

    def test_two_ids_that_used_to_collide_get_separate_pages(self):
        w = workspace('FULL1')
        w.exhibit('E4')['id'] = 'E-4'
        w.fact('F5')['sources'] = [{'ex': 'E-4'}]
        w.rec['deadlines'] = []
        self.assertEqual(w.home()[0], 0)
        self.assertIn('files/pages/E-4-1.jpg', tree(w.out))


if __name__ == '__main__':
    unittest.main()


@needs_pillow
class HtmlExhibits(Base):
    def test_a_script_in_a_shared_html_document_stops_the_build(self):
        for bad in ('<script>alert(1)</script>', '<p onclick="x()">hi</p>', '<iframe src="x.html"></iframe>', '<a href="javascript:x()">y</a>'):
            w = workspace('FULL1')
            with open(os.path.join(w.files, 'E5.html'), 'w') as fh:
                fh.write(f'<html><body>{bad}</body></html>')
            code, o = w.home()
            with self.subTest(bad=bad):
                self.assertEqual(code, 1, o)
                self.has('would run on the reader', o)
                self.has('E5.html', o)

    def test_a_remote_picture_is_noted(self):
        w = workspace('FULL1')
        with open(os.path.join(w.files, 'E5.html'), 'w') as fh:
            fh.write('<html><body><p>Hi</p><img src="https://tracker.example.com/p.gif"></body></html>')
        code, o = w.home()
        self.assertEqual(code, 0, o)
        self.has('tracker.example.com', o)

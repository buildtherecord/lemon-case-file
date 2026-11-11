"""Metadata removal: every kind of outgoing file is rewritten without its metadata and read back."""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))  # so these run from tests/, tools/views or the repo root
import os, shutil, unittest

from tests.helpers import Base, needs_pillow, needs_pdf_tools, needs_ffmpeg, tmpdir, seeds, scrub, HAVE_PIL, HAVE_POPPLER


@needs_pillow
class Images(Base):
    def setUp(self):
        d, _ = seeds()
        self.src = os.path.join(d, 'FULL1-files')
        self.out = tmpdir()

    def test_the_example_photo_really_carries_a_location_and_an_author(self):
        found = ' '.join(scrub.outgoing_problems(os.path.join(self.src, 'E7.jpg')))
        self.assertIn('GPS', found)
        self.assertIn('Author', found)

    def test_jpeg_loses_exif_and_gps(self):
        dst = os.path.join(self.out, 'E7.jpg')
        scrub.scrub_copy(os.path.join(self.src, 'E7.jpg'), dst)
        self.assertEqual(scrub.outgoing_problems(dst), [])
        from PIL import Image
        with Image.open(dst) as im:
            self.assertEqual(dict(im.getexif()), {})
            self.assertEqual(im.size, (600, 450))

    def test_png_loses_its_text_chunks(self):
        self.assertTrue(scrub.outgoing_problems(os.path.join(self.src, 'E2.png')))
        dst = os.path.join(self.out, 'E2.png')
        scrub.scrub_copy(os.path.join(self.src, 'E2.png'), dst)
        self.assertEqual(scrub.outgoing_problems(dst), [])
        from PIL import Image
        with Image.open(dst) as im:
            self.assertEqual(getattr(im, 'text', {}), {})

    def test_orientation_is_applied_before_the_tag_is_dropped(self):
        from PIL import Image
        im = Image.new('RGB', (40, 20), 'white')
        im.putpixel((0, 0), (255, 0, 0))
        ex = Image.Exif()
        ex[274] = 6   # rotate 90 clockwise to display
        src = os.path.join(self.out, 'rot.jpg')
        im.save(src, 'JPEG', exif=ex)
        dst = os.path.join(self.out, 'rot2.jpg')
        scrub.scrub_copy(src, dst)
        with Image.open(dst) as out:
            self.assertEqual(out.size, (20, 40))
            self.assertEqual(dict(out.getexif()), {})

    def test_comments_are_dropped_and_other_image_modes_work(self):
        from PIL import Image
        a = Image.new('P', (50, 40))
        a.putpalette([0, 0, 0, 255, 0, 0] * 128)
        b = a.copy()
        b.paste(1, (0, 0, 10, 10))
        a.save(os.path.join(self.out, 'anim.gif'), save_all=True, append_images=[b], loop=0, comment=b'secret comment')
        Image.new('L', (30, 30), 100).save(os.path.join(self.out, 'g.jpg'), comment=b'camera owner Jane')
        Image.new('RGBA', (30, 30), (255, 0, 0, 128)).save(os.path.join(self.out, 'rgba.png'))
        Image.new('CMYK', (30, 30)).save(os.path.join(self.out, 'cmyk.jpg'))
        for name, frames in (('anim.gif', 2), ('g.jpg', 1), ('rgba.png', 1), ('cmyk.jpg', 1)):
            src, dst = os.path.join(self.out, name), os.path.join(self.out, 'clean-' + name)
            scrub.scrub_copy(src, dst)
            with Image.open(dst) as im:
                self.assertEqual(getattr(im, 'n_frames', 1), frames, name)
                self.assertNotIn('comment', im.info, name)
            self.assertEqual(scrub.outgoing_problems(dst), [], name)

    def test_a_type_it_cannot_scrub_is_refused_in_plain_words(self):
        src = os.path.join(self.out, 'x.docx')
        with open(src, 'w') as fh:
            fh.write('x')
        with self.assertRaises(scrub.ScrubError) as cm:
            scrub.scrub_copy(src, os.path.join(self.out, 'y.docx'))
        self.assertIn('cannot scrub', str(cm.exception))


@needs_pdf_tools
class Pdfs(Base):
    def setUp(self):
        d, _ = seeds()
        self.src = os.path.join(d, 'FULL1-files', 'E1.pdf')
        self.out = tmpdir()

    def test_the_example_pdf_really_carries_author_subject_title_creator(self):
        found = ' '.join(scrub.outgoing_problems(self.src))
        for k in ('Author', 'Subject', 'Title', 'Creator'):
            self.assertIn(k, found)

    def test_scrubbed_pdf_has_none_of_them_and_keeps_its_pages(self):
        dst = os.path.join(self.out, 'E1.pdf')
        note = scrub.scrub_copy(self.src, dst)
        self.assertTrue(note)
        self.assertEqual(scrub.outgoing_problems(dst), [])
        info = scrub.pdf_info(dst)
        self.assertEqual(info['Pages'], '2')
        for k in scrub.BAD_PDF_KEYS:
            self.assertFalse(info.get(k), k)

    def test_the_picture_only_fallback_also_removes_everything(self):
        dst = os.path.join(self.out, 'fallback.pdf')
        note = scrub._image_only_pdf(self.src, dst)
        self.assertIn('image-only', note)
        self.assertEqual(scrub.outgoing_problems(dst), [])
        self.assertEqual(scrub.pdf_info(dst)['Pages'], '2')

    def test_embedded_javascript_is_detected_and_removed(self):
        try:
            import pypdf
        except ImportError:
            self.skipTest('pypdf is needed to make the test file')
        w = pypdf.PdfWriter(clone_from=self.src)
        w.add_js('app.alert("hi");')
        src = os.path.join(self.out, 'js.pdf')
        with open(src, 'wb') as fh:
            w.write(fh)
        self.assertIn('embedded JavaScript', scrub.outgoing_problems(src))
        dst = os.path.join(self.out, 'clean.pdf')
        scrub.scrub_copy(src, dst)
        self.assertEqual(scrub.outgoing_problems(dst), [])

    def test_page_images_are_named_by_id_and_capped(self):
        names, n = scrub.render_pdf_pages(self.src, self.out, 'E1', max_pages=1)
        self.assertEqual((names, n), (['E1-1.jpg'], 2))
        self.assertTrue(os.path.isfile(os.path.join(self.out, 'E1-1.jpg')))


@needs_ffmpeg
class Recordings(Base):
    def test_title_and_location_tags_are_gone_after_scrubbing(self):
        d, _ = seeds()
        src = os.path.join(d, 'FULL1-files', 'E8.mp4')
        found = ' '.join(scrub.outgoing_problems(src))
        self.assertIn('location', found)
        self.assertIn('title', found)
        dst = os.path.join(tmpdir(), 'E8.mp4')
        scrub.scrub_copy(src, dst)
        self.assertEqual(scrub.outgoing_problems(dst), [])
        self.assertGreater(os.path.getsize(dst), 1000)


class Html(Base):
    def test_author_meta_tags_and_saved_from_comments_are_removed(self):
        d = tmpdir()
        src = os.path.join(d, 'a.html')
        with open(src, 'w') as fh:
            fh.write('<!-- saved from url=(0040)https://mail.example.com/u/0/ --><html><head><meta name="author" content="Jane Doe"><meta name="generator" content="Word">'
                     '<title>T</title></head><body><!--[if IE]>keep<![endif]-->Hello</body></html>')
        self.assertEqual(len(scrub.outgoing_problems(src)), 2)
        dst = os.path.join(d, 'b.html')
        scrub.scrub_copy(src, dst)
        with open(dst) as fh:
            t = fh.read()
        self.assertEqual(scrub.outgoing_problems(dst), [])
        self.assertIn('Hello', t)
        self.assertNotIn('Jane', t)
        self.assertIn('<!--[if IE]>', t)


class Tools(Base):
    def test_the_doctor_runs_and_names_what_to_install(self):
        from tests.helpers import run
        code, o = run('doctor.py')
        self.has('INWARD pages', o)
        self.has('OUTWARD page', o)
        self.assertIn(code, (0, 1))
        self.lacks('Traceback', o)


if __name__ == '__main__':
    unittest.main()


class ExtractText(Base):
    def make_pdf(self, path, words):
        stream = f'BT /F1 14 Tf 72 700 Td ({words}) Tj ET'
        objs = ['<< /Type /Catalog /Pages 2 0 R >>', '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
                '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>',
                f'<< /Length {len(stream)} >>\nstream\n{stream}\nendstream', '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
        out, offs = b'%PDF-1.4\n', []
        for i, o in enumerate(objs, 1):
            offs.append(len(out))
            out += f'{i} 0 obj\n{o}\nendobj\n'.encode()
        x = len(out)
        out += f'xref\n0 {len(objs) + 1}\n0000000000 65535 f \n'.encode() + ''.join(f'{o:010d} 00000 n \n' for o in offs).encode()
        out += f'trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF\n'.encode()
        with open(path, 'wb') as fh:
            fh.write(out)

    @unittest.skipUnless(shutil.which('pdftotext'), 'pdftotext is needed')
    def test_text_is_read_from_pdf_html_and_txt_and_the_record_file_is_not_changed(self):
        import json, extract_text
        d = tmpdir()
        self.make_pdf(os.path.join(d, 'a.pdf'), 'We cannot locate a dealer to complete this recall.')
        with open(os.path.join(d, 'b.html'), 'w') as fh:
            fh.write('<html><head><style>p{}</style></head><body><p>Your case is &quot;under review&quot;.</p><script>x()</script></body></html>')
        with open(os.path.join(d, 'c.txt'), 'w') as fh:
            fh.write('Plain words.')
        rec = {'meta': {'title': 't', 'summary': 's', 'updated': 'u'}, 'facts': [],
               'exhibits': [{'id': 'E1', 'title': 'a', 'file': 'a.pdf'}, {'id': 'E2', 'title': 'b', 'file': 'b.html'}, {'id': 'E3', 'title': 'c', 'file': 'c.txt'},
                            {'id': 'E4', 'title': 'has text', 'file': 'c.txt', 'text': 'kept'}, {'id': 'E5', 'title': 'missing', 'file': 'nope.pdf'}]}
        new, report = extract_text.fill(rec, d)
        by = {e['id']: e for e in new['exhibits']}
        self.assertIn('cannot locate a dealer', by['E1']['text'])
        self.assertEqual(by['E2']['text'].split(), ['Your', 'case', 'is', '"under', 'review".'])
        self.assertEqual(by['E3']['text'], 'Plain words.')
        self.assertEqual(by['E4']['text'], 'kept')
        self.assertNotIn('text', rec['exhibits'][0])
        self.assertTrue(any('not in the files folder' in m for i, m in report if i == 'E5'))
        # the quote check now has something to check against
        from tests.helpers import checks
        def rec2(q):
            return {'meta': {'title': 't', 'summary': 'A letter.', 'updated': 'u'}, 'exhibits': new['exhibits'][:1],
                    'facts': [{'id': 'F1', 'date': '2026-01-01', 'status': 'documented', 'text': f'The maker wrote that it could “{q}.”', 'sources': [{'ex': 'E1'}]}]}
        _n, R = checks.check_record(rec2('cannot locate a dealer'))
        self.assertEqual((R.errors, R.verified), ([], 1))
        _n, R = checks.check_record(rec2('locate a dealer'))
        self.assertTrue(any("cut off a 'cannot'" in e for e in R.errors), R.errors)

    def test_a_scan_without_ocr_says_what_to_do(self):
        import extract_text
        from PIL import Image
        d = tmpdir()
        Image.new('RGB', (20, 20)).save(os.path.join(d, 'a.png'))
        _n, report = extract_text.fill({'exhibits': [{'id': 'E1', 'title': 'a', 'file': 'a.png'}]}, d)
        self.assertIn('--ocr', report[0][1])

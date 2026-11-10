"""Parse the cached Michigan Compiled Laws chapter XML (Internet Archive captures of legislature.mi.gov) into corpus.json. No network.

Usage: python -X utf8 parse.py 750 450 554 565 440   (the chapters to include)
Only each section's number, catch line, body text and its History line (the Legislative Service Bureau's source note) are
taken. The Editor's notes and Commentary (case-law annotations) are not copied.
"""
import hashlib
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from state_lib import Act, key, norm, sha, text_of, write_corpus

HERE = os.path.dirname(os.path.abspath(__file__))
C = Path(HERE) / '.cache'
TS = '20250311'
DATE = '2025-03-11'
RETRIEVED = '2026-10-30'
SITE = 'https://www.legislature.mi.gov/documents/mcl/'


def cap(ch):
    u = f'https://web.archive.org/web/{TS}id_/{SITE}Chapter%20{ch}.xml'
    p = C / hashlib.sha256(u.encode()).hexdigest()
    return p.read_bytes() if p.exists() else None


def body_lines(bt):
    """parse.py's reader, with fixes: a paragraph number holding markup ("(<Emph>l</Emph>)") is read whole (parse.py's
    findtext kept only "("); a paragraph heading is kept; content of a paragraph that is not a <P> (tables, <pre>
    blocks) is kept, one line per table row or per line of preformatted text."""
    root = ET.fromstring('<r>' + bt + '</r>')
    lines, sec = [], ''

    def para(p):
        head = []
        n = p.find('Paragraph-Number')
        num = ''.join(n.itertext()) if n is not None else ''
        if num.strip():
            head.append(num)
        h = p.find('Paragraph-heading')
        if h is not None and ''.join(h.itertext()).strip():
            head.append(''.join(h.itertext()))
        out, cur = [], list(head)
        for ch in p:
            if ch.tag in ('Paragraph-Number', 'Paragraph-heading', 'Paragraph'):
                continue
            if ch.tag == 'P':
                cur.append(''.join(ch.itertext()))
                continue
            rows = list(ch.iter('tr')) or [ch]
            for r in rows:
                txt = ''.join(r.itertext())
                for piece in (txt.split(chr(10)) if r.find('.//pre') is not None or ch.tag == 'pre' else [txt]):
                    piece = norm(piece)
                    if piece:
                        out.append(piece)
        first = norm(' '.join(cur))
        return ([first] if first else []) + out
    in_para = {id(h) for p in root.iter('Paragraph') for h in p.findall('Paragraph-heading')}
    for el in root.iter():
        if el.tag == 'Section-Number' and not sec:
            sec = norm(''.join(el.itertext()))
        elif el.tag == 'Paragraph-heading' and id(el) not in in_para:
            t = norm(''.join(el.itertext()))
            if t:
                lines.append(t)
        elif el.tag == 'Paragraph':
            ts = para(el)
            if ts:
                ts[0] = (sec + ' ' + ts[0]).strip() if sec else ts[0]
                lines += ts
                sec = ''
    if sec:
        lines.append(sec)
    return lines


def main(chapters):
    acts, srcs = [], []
    used = set()
    for ch in chapters:
        b = cap(ch)
        if b is None:
            raise SystemExit(f'not fetched: chapter {ch}')
        r = ET.fromstring(b.decode('utf-16').split('?>', 1)[1])
        ctitle = norm(r.findtext('Title') or '')
        for st in r.iter('MCLStatuteInfo'):
            name = norm(st.findtext('Name') or '')
            m = re.match(r'Act (\d+) of (\d+)', name)
            slug = key('mcl-act', f'{m.group(2)}-{m.group(1)}') if m else key('mcl-act', name)
            base, n = slug, 1
            while slug in used:
                n += 1
                slug = f'{base}-{n}'
            used.add(slug)
            short = norm(st.findtext('ShortTitle') or st.findtext('Heading') or '')
            a = Act(slug, f'MCL ch. {ch}, {name}', f'Michigan Compiled Laws, Chapter {ch} ({ctitle}): {name}' + (f', {short}' if short else ''),
                    f'{SITE}Chapter%20{ch}.xml', DATE, source_url=f'{SITE}Chapter%20{ch}.xml')
            a.sha256 = sha(b)
            for s in st.iter('MCLSectionInfo'):
                num = norm(s.findtext('MCLNumber') or '')
                if not num:
                    continue
                catch = norm(s.findtext('CatchLine') or '')
                lines = ['# MCL ' + num + (' ' + catch if catch else '')]
                bt = s.findtext('BodyText') or ''
                lines += body_lines(bt) if bt.strip() else []
                if len(lines) == 1:
                    lines.append('Repealed.' if s.findtext('Repealed') == 'true' else '')
                hist = s.findtext('HistoryText') or ''
                hs = [norm(''.join(ET.fromstring('<r>' + hist + '</r>').itertext())) for _ in [0]] if False else None
                if hist.strip():
                    items = [norm(''.join(h.itertext())) for h in ET.fromstring('<r>' + hist + '</r>').iter('HistoryData')]
                    items = [i for i in items if i]
                    if items:
                        lines.append('History: ' + '; '.join(items))
                a.add(key('sec', num), 'MCL ' + num, 'section', text_of(lines))
            acts.append(a)
        srcs.append(ch)
    country = {'code': 'US-MI', 'name': 'United States (Michigan)', 'slug': 'united-states-michigan', 'lang': 'en',
               'tz': 'America/Detroit', 'future_branch': 'future',
               'publisher': {'name': 'Michigan Legislative Council (legislature.mi.gov)', 'email': 'mcl@legislature-mi-gov.invalid'},
               'default_in_force_rule': {'text': 'No dated text history is published: each act is the oldest version available, dated by the day of the Internet Archive capture it was read from.',
                                         'source': SITE},
               'licence_note': 'Statute text is not copyrightable (Georgia v. Public.Resource.Org, 2020). Source: Michigan Legislative Council, legislature.mi.gov.'}
    sources = [{'name': 'Michigan Compiled Laws chapter XML (legislature.mi.gov), read from Internet Archive captures', 'url': SITE,
                'retrieved': RETRIEVED,
                'licence': 'Statute text carries no copyright (Georgia v. Public.Resource.Org, 2020). The Legislature states that the information "is not intended to replace official versions". No reuse restriction was found; the site\'s robots.txt could not be read because the host refuses connections from this machine.',
                'notes': 'Chapters ' + ', '.join(srcs) + '; section text and History line only.'}]
    decisions = [
        'legislature.mi.gov refuses connections from this machine, so each chapter file was read from an Internet Archive capture of 2025-03-11; no request was made to legislature.mi.gov itself and its robots.txt could not be read.',
        f'Each act is a single "oldest version available", dated {DATE}, the day of the capture. The XML also lists, for each section, the Acts that amended it with effective dates; that list is not used as history because the earlier texts are not available.',
        'One act per Michigan Act (statute) in a chapter file; one unit per section, keyed by its MCL number. The section\'s History line (for example "1931, Act 328, Eff. Sept. 18, 1931") is kept as its last line: it is the Legislative Service Bureau\'s source note.',
        'The Editor\'s notes and Commentary in the XML are annotations and are not copied.',
        'The Michigan Constitution of 1963 is not included: no capture of an official text was found within the time box.']
    write_corpus(HERE, country, sources, acts, decisions)


if __name__ == '__main__':
    sys.path.insert(0, HERE)
    main(sys.argv[1:])

"""Build a labelled older MCL version from an archived official chapter XML.

Usage: python -X utf8 history_capture.py CHAPTER CAPTURE_XML TIMESTAMP ARCHIVE_URL
The script only emits a new correction part; it never changes an existing part.
"""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import pathlib
import re
import sys

import parse_ia

HERE = pathlib.Path(__file__).resolve().parent


def effective_date_records(tree, section_numbers):
    """Read dated source notes with their actual XML field and section identity."""
    import xml.etree.ElementTree as ET
    records = []
    for section in tree.iter('MCLSectionInfo'):
        number = (section.findtext('MCLNumber') or '').strip()
        if number not in section_numbers:
            continue
        history = section.findtext('HistoryText') or ''
        history_tree = ET.fromstring('<r>' + history + '</r>')
        history_text = ''.join(history_tree.itertext())
        catchline = section.findtext('CatchLine') or ''
        fields = [('HistoryText', history_text)]
        if re.match(r'\s*Repealed\.', catchline):
            fields.append(('CatchLine', catchline))
        for field, text in fields:
            for match in re.finditer(r'\bEff\.\s+([A-Za-z]+\.?\s+\d{1,2},\s+\d{4})', text):
                date_text = match.group(1).replace('Sept.', 'Sep.')
                for fmt in ('%b. %d, %Y', '%B %d, %Y', '%b %d, %Y'):
                    try:
                        date = dt.datetime.strptime(date_text, fmt).date()
                        break
                    except ValueError:
                        continue
                else:
                    raise ValueError(f'Unparsed {field} effective date: {date_text}')
                records.append({'date': date.isoformat(), 'section': number,
                                'source_field': field,
                                'source_text': re.sub(r'\s+', ' ', text).strip()})
    if not records:
        raise ValueError('No effective date in source HistoryText or repeal CatchLine')
    return records


def date_basis(record, timestamp):
    return (f'Latest stated effective date among HistoryText notes and repeal CatchLine headings '
            f'in the official chapter XML captured {timestamp}: {record["date"]}. '
            f'Supporting source: MCL {record["section"]} {record["source_field"]}: '
            f'{record["source_text"]}')


def build(chapter, xml_path, timestamp, archive_url, *, write=True, hold_report=None, excluded_acts=None):
    original = HERE / 'corpus.d' / f'mcl-chapter-{chapter:04d}.json'
    if not original.exists() or not original.with_suffix('.PUBLISH').exists():
        raise ValueError(f'No published chapter part: {original.name}')
    raw = pathlib.Path(xml_path).read_bytes()
    # Some older XML snapshots qualify the metadata elements with a service namespace.
    # Strip XML namespace identifiers only, leaving every text node unchanged.
    import xml.etree.ElementTree as ET
    tree = ET.fromstring(raw.decode('utf-16') if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else raw.decode('utf-8-sig'))
    qualified = any('}' in el.tag for el in tree.iter())
    if qualified:
        for el in tree.iter():
            el.tag = el.tag.rsplit('}', 1)[-1]
    parse_raw = ET.tostring(tree, encoding='utf-8') if qualified else raw
    parse_ia.cached = lambda n: (parse_raw, timestamp) if n == chapter else (None, None)
    historical, msg = parse_ia.chapter(chapter)
    if historical is None:
        raise ValueError(msg)
    current = json.loads(original.read_text(encoding='utf-8'))
    old_by_slug = {a['slug']: a for a in historical['acts']}
    replacements = []
    capture_day = dt.date(int(timestamp[:4]), int(timestamp[4:6]), int(timestamp[6:8]))
    for present in current['acts']:
        if present['slug'] in (excluded_acts or set()):
            continue
        old = old_by_slug.get(present['slug'])
        if old is None:
            continue
        old_units = old['versions'][0]['units']
        current_version = present['versions'][0]
        if old_units == current_version['units']:
            continue
        try:
            records = effective_date_records(tree, {u['label'].removeprefix('MCL ') for u in old_units.values()})
            latest = max(records, key=lambda record: record['date'])
            source_day = dt.date.fromisoformat(latest['date'])
            if source_day > capture_day or source_day.isoformat() >= current_version['from']:
                raise ValueError(f'source effective date outside old-version range: {source_day}')
        except ValueError as exc:
            if hold_report is None:
                raise
            hold_report.append({'act': present['slug'], 'reason': str(exc)})
            continue
        version = copy.deepcopy(old['versions'][0])
        version['sha256'] = hashlib.sha256(raw).hexdigest()
        version['from'] = source_day.isoformat()
        version['source_url'] = archive_url
        version['in_force_basis'] = date_basis(latest, timestamp)
        version['text_as_of'] = capture_day.isoformat()
        version['note'] = (f'Official chapter XML in Internet Archive capture {timestamp}; '
                           f'latest effective date in section HistoryText notes and repeal CatchLine '
                           f'headings {source_day}; supporting field {latest["source_field"]} '
                           f'of MCL {latest["section"]}.')
        replacement = copy.deepcopy(present)
        replacement['url'] = archive_url
        replacement['versions'] = [version] + copy.deepcopy(present['versions'])
        replacements.append(replacement)
    if not replacements:
        raise ValueError('No earlier text differs from published text')
    out = {
        'corrects': original.name,
        'acts': replacements,
        'sources': [{
            'name': f'Michigan Compiled Laws chapter {chapter} XML, official text in Internet Archive capture {timestamp}',
            'url': archive_url,
            'retrieved': dt.date.today().isoformat(),
            'licence': 'Michigan statute and constitutional text is public domain.',
            'notes': f'Capture {timestamp}; SHA-256 {hashlib.sha256(raw).hexdigest()}.',
        }],
        'decisions': [f'Back-fill {len(replacements)} acts from official chapter {chapter} XML captured {timestamp}; '
                      'each older version starts on the latest effective date stated in its section HistoryText '
                      'notes and repeal CatchLine headings. '
                      'The published current version and text are retained unchanged.'],
        'ai_use': ['Code selected source dates and extracted XML deterministically; no model wrote law text.'],
    }
    path = HERE / 'corpus.d' / f'zz-history-{chapter:04d}-{timestamp[:8]}.json'
    if not write:
        return out
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(path.name, len(replacements), msg)
    for act in replacements:
        print(act['slug'], act['versions'][0]['from'], len(act['versions'][0]['units']))
    return out


if __name__ == '__main__':
    build(int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4])

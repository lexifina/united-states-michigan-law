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


def effective_dates(units):
    dates = []
    for unit in units.values():
        for raw in re.findall(r"\bEff\.\s+([A-Za-z]+\.?\s+\d{1,2},\s+\d{4})", unit['text']):
            raw = raw.replace('Sept.', 'Sep.')
            for fmt in ('%b. %d, %Y', '%B %d, %Y', '%b %d, %Y'):
                try:
                    dates.append(dt.datetime.strptime(raw, fmt).date())
                    break
                except ValueError:
                    continue
            else:
                raise ValueError(f'Unparsed effective date: {raw}')
    if not dates:
        raise ValueError('No source-stated effective dates')
    return dates


def build(chapter, xml_path, timestamp, archive_url):
    original = HERE / 'corpus.d' / f'mcl-chapter-{chapter:04d}.json'
    if not original.exists() or not original.with_suffix('.PUBLISH').exists():
        raise ValueError(f'No published chapter part: {original.name}')
    raw = pathlib.Path(xml_path).read_bytes()
    parse_ia.cached = lambda n: (raw, timestamp) if n == chapter else (None, None)
    historical, msg = parse_ia.chapter(chapter)
    if historical is None:
        raise ValueError(msg)
    current = json.loads(original.read_text(encoding='utf-8'))
    old_by_slug = {a['slug']: a for a in historical['acts']}
    replacements = []
    capture_day = dt.date(int(timestamp[:4]), int(timestamp[4:6]), int(timestamp[6:8]))
    for present in current['acts']:
        old = old_by_slug.get(present['slug'])
        if old is None:
            continue
        old_units = old['versions'][0]['units']
        current_version = present['versions'][0]
        if old_units == current_version['units']:
            continue
        dates = effective_dates(old_units)
        source_day = max(dates)
        if source_day > capture_day or source_day.isoformat() >= current_version['from']:
            raise ValueError(f'{present["slug"]}: source effective date outside old-version range: {source_day}')
        version = copy.deepcopy(old['versions'][0])
        version['from'] = source_day.isoformat()
        version['source_url'] = archive_url
        version['in_force_basis'] = (f'Latest effective date stated in section History lines of the '
                                     f'official chapter XML captured {timestamp}: {source_day}.')
        version['text_as_of'] = capture_day.isoformat()
        version['note'] = (f'Official chapter XML in Internet Archive capture {timestamp}; '
                           f'latest section History effective date {source_day}.')
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
                      'each older version starts on the latest effective date stated in its section History lines. '
                      'The published current version and text are retained unchanged.'],
        'ai_use': ['Code selected source dates and extracted XML deterministically; no model wrote law text.'],
    }
    path = HERE / 'corpus.d' / f'zz-history-{chapter:04d}-{timestamp[:8]}.json'
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    print(path.name, len(replacements), msg)
    for act in replacements:
        print(act['slug'], act['versions'][0]['from'], len(act['versions'][0]['units']))


if __name__ == '__main__':
    build(int(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4])

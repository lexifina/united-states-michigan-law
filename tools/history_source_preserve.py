"""Extract historical XML without changing source dash punctuation.

The existing chapter reader folds source em/en dashes to hyphens. Historical
source comparisons permit whitespace and quote normalization only. Keep the
original Unicode punctuation during deterministic extraction instead.
No network; no OCR; no changes to previously signed-off parts.
"""
import re

import history_capture
import parse_ia


def normalize_source(text):
    text = text.translate(str.maketrans({'\u2018': "'", '\u2019': "'",
                                        '\u201c': '"', '\u201d': '"'}))
    return re.sub(r'\s+', ' ', text).strip()


def source_text_of(lines):
    lines = [normalize_source(line) for line in lines]
    lines = [line for line in lines if line]
    return '\n'.join(lines) + '\n' if lines else ''


def extract(chapter, xml_path, timestamp, source_url, selected_slugs):
    """Reuse structural extraction with source-preserving text normalization."""
    import json
    original = history_capture.HERE / 'corpus.d' / f'mcl-chapter-{chapter:04d}.json'
    acts = json.loads(original.read_text(encoding='utf-8'))['acts']
    excluded = {act['slug'] for act in acts} - set(selected_slugs)
    previous_norm, previous_text_of = parse_ia.norm, parse_ia.text_of
    try:
        parse_ia.norm = normalize_source
        parse_ia.text_of = source_text_of
        part = history_capture.build(chapter, xml_path, timestamp, source_url,
                                     write=False, excluded_acts=excluded)
    finally:
        parse_ia.norm, parse_ia.text_of = previous_norm, previous_text_of
    for act in part['acts']:
        act['versions'][0]['source_images'] = 0
    part['decisions'].append('Historical XML extraction preserves source dash punctuation; '
                             'only whitespace and typographic quotes are normalized.')
    return part

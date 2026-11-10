"""Writes repo/README.md, LICENSE and jurisdiction.json for corpus.json plus every signed-off corpus.d part
(mcl-chapter-*.json with a .PUBLISH). One table row per MCL chapter (a chapter holds many Acts). No network.
    python -X utf8 docs_ia.py
"""
import json, os, re
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, 'repo')
NL = '\n'


def ch_of(url):
    return int(re.search(r'Chapter%20(\d+)\.xml', url).group(1))


rows = OrderedDict()
c = json.load(open(os.path.join(HERE, 'corpus.json'), encoding='utf-8'))
parts = sorted(f for f in os.listdir(os.path.join(HERE, 'corpus.d')) if f.endswith('.json')
               and os.path.exists(os.path.join(HERE, 'corpus.d', f[:-5] + '.PUBLISH')))
acts = list(c['acts'])
for f in parts:
    acts += json.load(open(os.path.join(HERE, 'corpus.d', f), encoding='utf-8'))['acts']
for a in acts:
    n = ch_of(a['url'])
    t = re.match(r'Michigan Compiled Laws, Chapter \d+ \((.*?)\):', a['title'])
    r = rows.setdefault(n, {'title': t.group(1) if t else '', 'acts': 0, 'sections': 0, 'dates': set(), 'folders': []})
    r['acts'] += 1
    r['sections'] += len(a['versions'][-1].get('units') or {})
    r['dates'].add(a['versions'][0]['from'])
    r['folders'].append(a['slug'])
table = NL.join(
    f"| {n} | {r['title'][:1] + r['title'][1:].lower() if r['title'].isupper() else r['title']} | {r['acts']} | {r['sections']} | "
    f"{', '.join(sorted(r['dates']))} | `{r['folders'][0]}/`" + (f" .. `{r['folders'][-1]}/`" if len(r['folders']) > 1 else '') + ' |'
    for n, r in sorted(rows.items()))
nact = sum(r['acts'] for r in rows.values())
nsec = sum(r['sections'] for r in rows.values())

readme = f"""# United States (Michigan): law history in git

Part of [lexifina/global-law](https://github.com/lexifina/global-law), one git history for every country's law: this is the law of Michigan, United States, which global-law reads at `united-states/michigan/acts/`.

The law of Michigan as a git history: one file per provision, with `git blame` and `git log` working line by line. It follows the shared design of [lexifina/global-law](https://github.com/lexifina/global-law).

**What is in it now (not complete)**: {len(rows)} chapters of the Michigan Compiled Laws, {nact} Acts, {nsec} sections. Each Act is a folder; MCL chapter 1 is the Constitution of 1963.

| MCL chapter | Chapter title | Acts | Sections | Text as of | Folders |
| ---: | --- | ---: | ---: | --- | --- |
{table}

**Source.** The Michigan Compiled Laws chapter files (XML) published by the [Michigan Legislature](https://www.legislature.mi.gov/), read from Internet Archive captures of those files. English. Only the section number, catch line, body text (including tables and paragraph headings) and the section's History line are taken; the Editor's notes and Commentary (case annotations) are not.

## Dates

The Legislature's files carry the current text only. Each Act is therefore one version, "oldest version available", dated by the day of the Internet Archive capture of its chapter file (the file states no currency date): 2025-03-11 for the five chapters of the first build, and the newest capture of each file for the chapters added on 2026-11-10. The XML lists the Acts that amended each section and their effective dates, but the earlier texts are not available, so that list is not history here; later builds will add later versions on top.

## How it is checked

Every version is read back from git on the day it took effect and on the day before (`tools/check_repo.py`) and must match `corpus.json` and its parts; the results are in `REPRODUCE.md`. Each added chapter was also compared with its source file: every section in the file has a file here, and its letters and digits equal the file's.

## What "author" means

The author of a commit is the law that made the change, with an e-mail address that cannot exist. No dated history is available, so every commit is credited to the publisher as "oldest version available". The committer is always Lexifina.

## Limits

Chapters whose file the Internet Archive does not hold are not included yet; the Public Acts are not included. There is no history before the dates above. The five chapters of the first build (440, 450, 554, 565, 750) were read with an earlier reader that dropped tables, paragraph headings and some paragraph numbers inside a few sections; the chapters added later do not have that defect.
"""
open(os.path.join(R, 'README.md'), 'w', encoding='utf-8', newline=NL).write(readme)

lic = open(os.path.join(R, 'LICENSE'), encoding='utf-8').read()
lic = re.sub(r'\(read from Internet Archive captures of 2025-03-11; retrieved 2026-10-30\)',
             '(read from Internet Archive captures of the chapter files: 2025-03-11 for the first build, retrieved 2026-10-30; the newest capture of each file for the chapters added 2026-11-10)', lic)
open(os.path.join(R, 'LICENSE'), 'w', encoding='utf-8', newline=NL).write(lic)
j = json.load(open(os.path.join(R, 'jurisdiction.json'), encoding='utf-8'))
j['build'] = f'built: {len(rows)} MCL chapters ({nact} Acts, {nsec} sections) incl. the Constitution of 1963 (MCL chapter 1), one version each from Internet Archive captures'
open(os.path.join(R, 'jurisdiction.json'), 'w', encoding='utf-8', newline=NL).write(json.dumps(j, indent=2) + NL)
print(len(rows), 'chapters', nact, 'acts', nsec, 'sections')

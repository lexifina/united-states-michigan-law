"""Writes repo/README.md, LICENSE, jurisdiction.json from corpus.json."""
import json
import os

from state_lib import write_docs

HERE = os.path.dirname(os.path.abspath(__file__))
c = json.load(open(os.path.join(HERE, 'corpus.json'), encoding='utf-8'))
rows = []
for a in c['acts']:
    rows.append((a['slug'] + '/', a['title'], 1, f"{len(a['versions'][0]['units'])} sections, text as of 2025-03-11"))
write_docs(HERE, {
    'name': 'United States (Michigan)', 'state': 'Michigan', 'code': 'US-MI', 'slug': 'michigan',
    'domain': 'legislature.mi.gov', 'acts_table': rows,
    'source': 'The Michigan Compiled Laws chapter files (XML) of the [Michigan Legislature](https://www.legislature.mi.gov/), read from Internet Archive captures because legislature.mi.gov refuses connections from the build machine. English. Only the section number, catch line, body text and the section\'s History line are taken; the Editor\'s notes and Commentary (case annotations) are not.',
    'dates': 'The Legislature\'s files carry the current text only. Each Act is therefore one version, "oldest version available", dated 2025-03-11, the day of the Internet Archive capture read. The XML lists the Acts that amended each section and their effective dates, but the earlier texts are not available, so that list is not history here; later builds will add later versions on top.',
    'limits': 'A first build: a few chapters of the Michigan Compiled Laws (the Michigan Penal Code and other selected Acts). The other chapters, the Michigan Constitution of 1963 and the Public Acts are not included. There is no history before the date above.',
    'license': """Source: Michigan Compiled Laws, Michigan Legislature, https://www.legislature.mi.gov/ (read from Internet Archive captures of 2025-03-11; retrieved 2026-10-30).

Statute text is not copyrightable: under the government edicts doctrine, as the Supreme Court applied it in Georgia v.
Public.Resource.Org, Inc., 590 U.S. 255 (2020), no one holds copyright in the laws that legislators make in their official
capacity. The Legislature states that its online information "is not intended to replace official versions"; no restriction on
reuse of the statute text was found. The Editor's notes and Commentary in the Legislature's files (annotations) are not used.""",
    'publisher': 'Michigan Legislative Council, legislature.mi.gov', 'build': 'built', 'date': '2026-10-30',
})

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Knowledge Graph (RAG)

A graphify knowledge graph of this entire codebase and all PDFs lives at `graphify-out/graph.json` (292 nodes, 314 edges). **Always query this graph before opening any file.** It covers all parsers, Flask routes, PDF data schemas, college codes, categories, and quota types.

To query it:
```bash
python3 -c "
import json
from networkx.readwrite import json_graph
import networkx as nx
from pathlib import Path

data = json.loads(Path('graphify-out/graph.json').read_text())
G = json_graph.node_link_graph(data, edges='links')
terms = [t.lower() for t in 'YOUR QUESTION HERE'.split() if len(t) > 3]
scored = sorted([(sum(1 for t in terms if t in G.nodes[n].get('label','').lower()), n) for n in G.nodes()], reverse=True)
start_nodes = [nid for _, nid in scored[:3] if _ > 0]
frontier = set(start_nodes)
visited = set(start_nodes)
for _ in range(3):
    nxt = set()
    for n in frontier:
        for nb in G.neighbors(n):
            if nb not in visited:
                nxt.add(nb)
    visited.update(nxt); frontier = nxt
for nid in list(visited)[:30]:
    d = G.nodes[nid]
    print(d.get('label', nid), '|', d.get('source_file',''))
"
```

Only fall back to direct file reads when the graph lacks detail. Interactive: `/graphify query "<question>"`

## Commands

```bash
# Quick setup (cross-platform scripts in repo root)
./install.sh && ./start.sh   # Linux/Mac
install.bat && start.bat     # Windows

# Install dependencies
pip install -r requirements.txt

# Run locally (http://127.0.0.1:5000)
python app.py

# Environment variables (optional .env file)
# MAX_UPLOAD_MB=500   # default 500; set to 4 on Vercel (platform limit)

# Run a parser standalone (operates on largest PDF in current directory)
python final.py       # UG parser
python parse_pg.py    # PG parser
```

## Architecture

This is a Flask web app that parses Maharashtra NEET selection list PDFs and exports them as Excel files.

**Request flow:**
1. `templates/index.html` — frontend with drag-and-drop upload and `type` field (`ug` or `pg`)
2. `app.py` — Flask routes; `/upload` dispatches to the correct parser based on `exam_type`
3. `final.py` — UG parser (`parse_student_list_to_excel`): extracts text via PyMuPDF, matches rows with regex against `Sr.No AIR NeRollNo CETFormNo NAME GENDER rest...`, then resolves category/quota/college
4. `parse_pg.py` — PG parser (`parse_pg_pdf`): same text-extraction approach but a different row format anchored on a 4-char subject code (`XXXXS/I/N : SUBJECT NAME`)

**Vercel deployment:**
- `api/index.py` is the serverless entry point — it just re-exports the Flask `app` object from `app.py`
- `vercel.json` routes all requests to `api/index.py`
- `MAX_UPLOAD_MB` must be set to `4` on Vercel (platform file-size limit)

## Parser Details

**UG (`final.py`):**
- Output columns: `Sr. No., AIR, NEET Roll No., CET Form No., Name, Gender, Category, Quota, College Code, College Name` (10 cols)
- Data rows trigger on `"Sr. AIR NEET"` header line, then match regex: `^\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\$?[A-Z\s.]+?)\s+([MF])\s+(.*)`
- `$` prefix on names = minority marker (stripped before saving)
- College identified by `DDDD: College Name` pattern
- Status markers `(Ret.)`, `(No Pref.)`, `(No Change)` are stripped from College Name and appended to Quota

**PG (`parse_pg.py`):**
- Output columns: `Sr. No., SML, I/IB, Form No., Name, Category, Subject Code, Subject, College, Place, Quota, Remarks, Remarks (Combined)` (13 cols)
- Data rows trigger on `SrNo SML FormNo` header, then match: `^\s*(\d+)(IB?\s*-)?\s*(\d+(?:\.\d+)?)\s+(\d{9})\s+(.*)`
- `I-` = inservice with incentive marks; `IB-` = inservice without
- Subject code suffix: `S`=regular, `I`=in-service, `N`=NRI
- `KNOWN_CATEGORIES` includes NRI, ORC, ORA, NTD/NTC/NTB PWD — longest-match first
- `_QUOTA_RE` covers 50+ quota patterns: IS*/ISPH*, PH-hyphenated, ORPHAN-C with single-letter suffix, ORPHAN SEB (truncated), EM* variants
- `_KNOWN_SUBJECTS` guards against multi-word subjects (Emergency & Critical, Immunology, Physical Medicine) bleeding into College
- College and Place are split on 2+ consecutive spaces; `_KNOWN_PLACE_PATTERNS` fallback handles single-space cases
- `_clean_bleeding_place()` post-processing pass rescues quota/remark text that bled into Place column
- Two-pass `trailing_match` (before and after paren-stripping) handles bare PH hidden behind `(Ret.)`
- Category defaults to blank (not "OPEN") for general-category candidates

## Gotchas

- **UG `known_categories` is inside `extract_category_quota()`** — defined at line ~109 of `final.py`, not at module level. Extend it there, not at the top of the file like PG's `KNOWN_CATEGORIES`.
- **`AIOPEN` quota (UG Round 4+)** — All India Open seats appear as category `AIOPEN` with quota `(A.I.)`. Parsers treat this as distinct from `OPEN`; don't merge them.
- **`graphify-out/` is untracked** — graph files are gitignored. Run `/graphify . --update` after modifying `final.py` or `parse_pg.py` to keep the RAG graph current.
- **PG status markers appear in two positions** — sometimes before `(Ret.)`, sometimes hidden behind it. The two-pass `trailing_match` in `parse_right_side` is intentional; don't simplify it to one pass.

## Running Parsers on Specific PDFs

```bash
# Batch-parse all PG PDFs
python3 -c "
from parse_pg import parse_pg_pdf; import os
for pdf in ['pg-pdf/NEET PG 2025 MAHARASHTRA STATE 1ST ROUND SELECTION LIST.pdf',
            'pg-pdf/NEET PG 2025 MAHARASHTRA STATE 3RD ROUND SELECTION LIST.pdf',
            'pg-pdf/NEET PG 2025 MAHARASHTRA STATE STRAY VACANCY ROUND SELECTION LIST.pdf',
            'pg-pdf/NEET PG 2025 Maharashtra Stray Vacancy Round 2 Selection List.pdf']:
    parse_pg_pdf(pdf, os.path.splitext(pdf)[0] + '_Parsed.xlsx')
"

# Batch-parse all UG PDFs
python3 -c "
from final import parse_student_list_to_excel; import os
for pdf in sorted([f'ug-pdf/{f}' for f in os.listdir('ug-pdf') if f.lower().endswith('.pdf')]):
    parse_student_list_to_excel(pdf, os.path.splitext(pdf)[0] + '_Parsed.xlsx')
"
```

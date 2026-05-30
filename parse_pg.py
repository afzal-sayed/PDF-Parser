# Author: Afzal Sayed
# Email:  afzal.sayed04@gmail.com
# GitHub: github.com/afzal-sayed
# LinkedIn: linkedin.com/in/afzal-sayed

import fitz
import pandas as pd
import re
import os
from datetime import datetime

# Compound categories must come before single-word ones (longest match first)
KNOWN_CATEGORIES = [
    "EWS MIN", "OBC MIN", "SC MIN", "ST MIN", "SEBC MIN",
    "VJA MIN", "NTD MIN", "NTC MIN", "NTB MIN",
    "OBC PWD", "SC PWD", "ST PWD", "EWS PWD", "SEBC PWD", "VJA PWD",
    "NTD PWD", "NTC PWD", "NTB PWD",
    "ST ORA",
    "OPEN", "OBC", "SC", "ST", "EWS", "SEBC", "NTC", "NTB", "NTD", "VJA",
    "MIN", "PWD", "NRI", "MINORITY", "ORC", "ORA",
]

# Subjects that use only a single space before the college name in certain PDFs.
# When the subject regex bleeds into the college field, we trim at these known boundaries.
_KNOWN_SUBJECTS = {
    "EMERGENCY & CRITICAL",
    "IMMUNOLOGY HAEMATOLO",
    "PHYSICAL MEDICINE",
    "NUCLEAR MEDICINE",
    "PHYSICAL MEDICINE & REHAB",
}

# Categories whose presence in the quota already encodes the caste component —
# suppress extracting that caste separately into the Category column.
_EM_QUOTA_CATS = {
    "EMOBC": "OBC", "EMSC": "SC", "EMST": "ST", "EMEWS": "EWS",
    "EMSEBC": "SEBC", "EMNTB": "NTB", "EMNTC": "NTC", "EMNTD": "NTD", "EMVJA": "VJA",
}

# Known Maharashtra city/place tokens used to split college+place when only single space separates them
_KNOWN_PLACES = {
    "MUMBAI", "NAGPUR", "PUNE", "NASHIK", "NASIK", "THANE", "PUNE", "LATUR",
    "AURANGABAD", "SAMBHAJINA", "SOLAPUR", "KOLHAPUR", "AMRAVATI", "NANDED",
    "JALGAON", "AKOLA", "DHULE", "NANDURBAR", "AHMEDNAGAR", "AHILYANAGA",
    "RATNAGIRI", "SINDHUDURG", "PALGHAR", "GONDIA", "CHANDRAPUR", "YAVATMAL",
    "YEOTMAL", "BARAMATI", "MIRAJ", "AMBAJOGAI", "JALNA", "BEED", "OSMANABAD",
    "KARJAT", "PIMPARI", "TALEGAON",
}

# Multi-word place suffixes (checked against end of college_loc string)
_KNOWN_PLACE_PATTERNS = re.compile(
    r'\s+((?:JUHU,?\s*MUMB(?:AI)?|NEW\s+MUMBAI|PIMPARI,?\s*(?:PUNE|P)|'
    r'TALEGAON\s*P?|ISLAMPUR,?\s*S?|SEVAGRAM,?\s*W?|NANDI\s*HILLS?|'
    r'SAMBHAJI\s*NAGAR|' +
    r'|'.join(re.escape(p) for p in sorted(_KNOWN_PLACES, key=len, reverse=True)) +
    r'))\s*$',
    re.IGNORECASE,
)

# Priority-ordered quota regex (most specific first to avoid partial matches)
_QUOTA_RE = re.compile(
    r'\s+(ISPH\s+(?:EWS|OBC|SC|ST|SEBC|NTC|NTB|NTD|VJA|MIN)'
    r'|IS\s+(?:PH|EM(?:OBC|SEBC|NTB|NTC|NTD|VJA)|OPEN|OBC|SC|ST|EWS|SEBC|NTC|NTB|NTD|VJA|MIN)'
    r'|PH-(?:OPEN|OBC|SC|ST|EWS|SEBC|NTC|NTB|NTD|VJA)'
    r'|ORPHAN\s*-?\s*C(?:\s+(?:EWS|OBC|SC|SEBC|NTC|NTB|NTD|VJA|ST|MIN|[A-Z]))?'
    r'|ORPHAN\s+(?:SEBC|SEB|EWS|OBC|SC|NTC|NTB|NTD|VJA|ST)'
    r'|PH\s+(?:OPEN|OBC|SC|ST|EWS|SEBC|NTC|NTB|NTD|VJA)'
    r'|EM(?:OPEN|OBC|SC|ST|EWS|SEBC|NTC|NTB|NTD|VJA)'
    r'|(?:OPEN|OBC|SC|ST|EWS|SEBC|NTC|NTB|NTD|VJA|MIN|MINORITY)'
    r'|I\.Q\.|NRI|ORPHAN)\s*$'
)

# Known quota-only tokens that can mistakenly end up as the entire Place value
_QUOTA_ONLY_TOKENS = frozenset({
    'NRI', 'PH', 'OPEN', 'OBC', 'SC', 'ST', 'EWS', 'SEBC',
    'NTB', 'NTC', 'NTD', 'VJA', 'MIN', 'ORPHAN', 'I.Q.',
})


def extract_name_category(text):
    text = text.strip()
    for cat in KNOWN_CATEGORIES:
        if text.endswith(' ' + cat):
            return text[:-len(cat) - 1].strip(), cat
    return text, ""


def parse_right_side(text):
    """Extract college, place, quota, and remarks from the right portion of a data line.

    Returns (college, place, quota, remarks) — all four separately so callers
    can build the Remarks (Combined) column as f"{quota} {remarks}".strip().
    """
    text = text.strip()

    # 1. Strip trailing bare-word remarks.
    #    Hyphenated PH codes (PH-SC, PH-OBC) and IPH appear as remark labels at line end.
    #    NRI is intentionally NOT listed — it must be caught by the quota regex instead.
    trailing_match = re.search(
        r'\s+(Inter-se(?:\s+(?:INS|ALL|[A-Z0-9]+))?'
        r'|Against(?:\s+[A-Z]+(?:-[A-Z]+)?(?:\s+[A-Z]+)?)?'
        r'|Ins-[A-Z]+'
        r'|PH-(?:OPEN|OBC|SC|ST|EWS|SEBC|NTC|NTB|NTD|VJA)'
        r'|IPH|I-PH'
        r'|PH)\s*$',
        text
    )
    trailing = trailing_match.group(1).strip() if trailing_match else ""
    if trailing_match:
        text = text[:trailing_match.start()].strip()

    # 2. Strip trailing parenthesised markers: (Ret.), (EMD), (No Pref), (No Change), etc.
    # Allow optional closing paren to handle PDF lines where paren was split across lines.
    status_match = re.search(r'((?:\s*\([A-Za-z./ ]+\)?)+)\s*$', text)
    status = status_match.group(1).strip() if status_match else ""
    if status_match:
        text = text[:status_match.start()].strip()

    # 2b. Second pass of trailing_match after parens are removed.
    # Fixes cases like "PH OPEN    PH  (Ret.)" where the bare "PH" remark was hidden
    # behind "(Ret.)" and missed by the first pass.
    _TRAILING_RE = re.compile(
        r'\s+(Inter-se(?:\s+(?:INS|ALL|[A-Z0-9]+))?'
        r'|Against(?:\s+[A-Z]+(?:-[A-Z]+)?(?:\s+[A-Z]+)?)?'
        r'|Ins-[A-Z]+'
        r'|PH-(?:OPEN|OBC|SC|ST|EWS|SEBC|NTC|NTB|NTD|VJA)'
        r'|IPH|I-PH'
        r'|PH)\s*$'
    )
    trailing_match2 = _TRAILING_RE.search(text)
    if trailing_match2:
        extra = trailing_match2.group(1).strip()
        trailing = (trailing + ' ' + extra).strip() if trailing else extra
        text = text[:trailing_match2.start()].strip()

    # trailing comes first ("PH (Ret.)" not "(Ret.) PH") to match reference format
    remarks = " ".join(filter(None, [trailing, status]))

    # 3. Match quota (priority-ordered: most specific patterns first)
    quota_match = _QUOTA_RE.search(text)
    if quota_match:
        quota_base = quota_match.group(1).strip()
        college_loc = text[:quota_match.start()].strip()
    else:
        quota_base = ""
        college_loc = text

    # 4. Split college_loc into college and place.
    #    Primary: split on 2+ consecutive spaces (PDF column separator).
    #    Fallback: match a known city token at the end of the string.
    parts = re.split(r'\s{2,}', college_loc, 1)
    if len(parts) > 1:
        college = parts[0].strip()
        place = parts[1].strip()
    else:
        place_match = _KNOWN_PLACE_PATTERNS.search(college_loc)
        if place_match:
            college = college_loc[:place_match.start()].strip()
            place = place_match.group(1).strip()
        else:
            college = college_loc.strip()
            place = ""

    return college, place, quota_base, remarks


def _clean_bleeding_place(df):
    """Post-processing safety net: move quota/remark text that bled into Place back
    to the correct columns.  Handles:
      A) Place = "CITY   QUOTA   REMARK"  (city + extra, any spacing)
      B) Place = "NRI" / "PH"             (pure quota token, no city)
    """

    def _safe(val):
        """Stripped string, treating NaN/'nan'/'N/A' as empty."""
        if val is None:
            return ''
        try:
            import math
            if isinstance(val, float) and math.isnan(val):
                return ''
        except Exception:
            pass
        s = str(val).strip()
        return '' if s.lower() in ('nan', 'none', 'n/a', 'na') else s

    def _apply(idx, city, quota, remark=''):
        df.at[idx, 'Place'] = city
        if quota and not _safe(df.at[idx, 'Quota']):
            df.at[idx, 'Quota'] = quota
        q = _safe(df.at[idx, 'Quota'])
        r = _safe(df.at[idx, 'Remarks'])
        if remark and not r:
            df.at[idx, 'Remarks'] = remark
            r = remark
        df.at[idx, 'Remarks (Combined)'] = (q + ' ' + r).strip() if r else q

    for idx, row in df.iterrows():
        place = _safe(row['Place'])
        if not place:
            continue

        # Case B: entire Place value is a bare quota token (city missing)
        if place in _QUOTA_ONLY_TOKENS:
            if not _safe(row['Quota']):
                df.at[idx, 'Quota'] = place
            df.at[idx, 'Place'] = ''
            continue

        # Case A: search for a quota token in the Place string.
        # First strip any trailing bare remark codes (PH, IPH, PH-SC …) that would
        # shadow the real quota ("PH OPEN    PH" → strip trailing "PH" → "PH OPEN").
        _TRAILING_REMARK_IN_PLACE = re.compile(
            r'\s+(PH-(?:OPEN|OBC|SC|ST|EWS|SEBC|NTC|NTB|NTD|VJA)|IPH|I-PH|PH)\s*$'
        )
        remark_trail = _TRAILING_REMARK_IN_PLACE.search(place)
        remark_suffix = remark_trail.group(1).strip() if remark_trail else ''
        search_place = place[:remark_trail.start()].strip() if remark_trail else place

        # _QUOTA_RE requires a leading \s+ so prepend a space.
        q_match = _QUOTA_RE.search(' ' + search_place)
        if not q_match:
            continue

        # q_match.start() is in ' '+search_place; subtract 1 to get index in search_place.
        quota_start = q_match.start() - 1
        city = search_place[:quota_start].strip()
        quota = q_match.group(1).strip()
        remark = remark_suffix

        # If city part itself has double-space noise (rare), take only the first token
        if '  ' in city:
            city = re.split(r'\s{2,}', city, 1)[0].strip()

        if city:
            _apply(idx, city, quota, remark)
        elif quota and not _safe(row['Quota']):
            df.at[idx, 'Quota'] = quota

    return df


def parse_pg_pdf(pdf_path, excel_path):
    """
    Extracts student selection data from a Maharashtra NEET PG selection list PDF
    and saves it to an Excel file.

    Output columns: Sr. No., SML, I/IB, Form No., Name, Category, Subject Code,
                    Subject, College, Place, Quota, Remarks, Remarks (Combined)
    """
    if not os.path.exists(pdf_path):
        print(f"Error: '{pdf_path}' not found.")
        return

    print(f"Opening PDF: {pdf_path}...")

    try:
        doc = fitz.open(pdf_path)
        print(f"PDF has {len(doc)} pages...")

        full_text = ""
        for page_num, page in enumerate(doc):
            if page_num % 10 == 0:
                print(f"Processing page {page_num + 1}/{len(doc)}...")
            full_text += page.get_text("text") + "\n"
        doc.close()
        print("Text extraction complete.")

    except Exception as e:
        print(f"Error reading PDF: {e}")
        return

    # Join multi-line status markers like "(No\n   Pref)" → "(No Pref)"
    full_text = re.sub(r'\(No\s+(Pref|Change)\)', r'(No \1)', full_text)

    lines = full_text.split('\n')
    extracted_data = []
    data_started = False

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Detect header row
        if 'SrNo' in line and 'SML' in line and 'FormNo' in line:
            data_started = True
            continue

        if line.startswith('---') or line.startswith('Legends') or not data_started:
            continue

        # Match: SrNo [I-/IB-] SML FormNo rest...
        # I-  = inservice with incentive marks
        # IB- = inservice without incentive marks
        header_match = re.match(r'^\s*(\d+)(IB?\s*-)?\s*(\d+(?:\.\d+)?)\s+(\d{9})\s+(.*)', line)
        if not header_match:
            continue

        sr_no = header_match.group(1)
        # Normalise I-/IB- prefix to "I" or "IB" (strip the dash)
        ib_raw = (header_match.group(2) or "").strip().rstrip('-').strip()
        sml = header_match.group(3)
        form_no = header_match.group(4)
        rest = header_match.group(5).strip()

        # --- Choice Not Available ---
        if "Choice Not Available" in rest:
            name_cat = rest.split("Choice Not Available")[0].strip()
            name, category = extract_name_category(name_cat)
            extracted_data.append({
                "Sr. No.": int(sr_no),
                "SML": sml,
                "I/IB": ib_raw,
                "Form No.": form_no,
                "Name": name,
                "Category": category,
                "Subject Code": "Choice Not Available",
                "Subject": "Choice Not Available",
                "College": "Choice Not Available",
                "Place": "Choice Not Available",
                "Quota": "Choice Not Available",
                "Remarks": "",
                "Remarks (Combined)": "Choice Not Available",
            })
            continue

        # --- Disqualified ---
        if "Disqualified" in rest:
            name_cat = rest.split("Disqualified")[0].strip()
            name, category = extract_name_category(name_cat)
            extracted_data.append({
                "Sr. No.": int(sr_no),
                "SML": sml,
                "I/IB": ib_raw,
                "Form No.": form_no,
                "Name": name,
                "Category": category,
                "Subject Code": "Disqualified",
                "Subject": "Disqualified",
                "College": "Disqualified",
                "Place": "Disqualified",
                "Quota": "Disqualified",
                "Remarks": "",
                "Remarks (Combined)": "Disqualified",
            })
            continue

        # --- Normal row: anchor on subject code XXXX[S/I/N] : SUBJECT ---
        # Suffix S=regular, I=in-service, N=NRI
        # Use strict double-space boundary so subject names like "Emergency & Critical Care"
        # don't bleed into the college field. Fall back to end-of-string only if needed.
        subj_match = re.search(r'(\d{4}[A-Z])\s*:\s*([A-Z][A-Z\s&/.()\-]{1,40}?)(?=\s{2,})', rest)
        if not subj_match:
            subj_match = re.search(r'(\d{4}[A-Z])\s*:\s*([A-Z][A-Z\s&/.()\-]{1,40}?)\s*$', rest)
        if not subj_match:
            continue

        name_cat = rest[:subj_match.start()].strip()
        subj_code = subj_match.group(1)
        subj_name = subj_match.group(2).strip()
        after_subj = rest[subj_match.end():].strip()

        # Fix: subject name may bleed into college when PDF uses single space between them.
        # Check against known multi-word subjects and push the extra text back to after_subj.
        for ks in sorted(_KNOWN_SUBJECTS, key=len, reverse=True):
            if subj_name.startswith(ks) and len(subj_name) > len(ks):
                # Strip leading punctuation/spaces from bleed before pushing back to after_subj
                bleed = re.sub(r'^[\s&/()\-]+', '', subj_name[len(ks):]).strip()
                subj_name = ks
                if bleed:
                    after_subj = (bleed + ("  " if after_subj else "") + after_subj).strip()
                break
        # Strip any orphan trailing "&" or "/" from partial subject capture
        subj_name = re.sub(r'[\s&/]+$', '', subj_name).strip()

        name, category = extract_name_category(name_cat)
        college, place, quota_base, remarks = parse_right_side(after_subj)

        remarks_combined = (quota_base + " " + remarks).strip() if remarks else quota_base

        extracted_data.append({
            "Sr. No.": int(sr_no),
            "SML": sml,
            "I/IB": ib_raw,
            "Form No.": form_no,
            "Name": name,
            "Category": category,
            "Subject Code": subj_code,
            "Subject": subj_name,
            "College": college,
            "Place": place,
            "Quota": quota_base,
            "Remarks": remarks,
            "Remarks (Combined)": remarks_combined,
        })

        if len(extracted_data) % 500 == 0:
            print(f"Extracted {len(extracted_data)} records...")

    if not extracted_data:
        print("❌ No records found.")
        print("Check that the PDF is a text-based Maharashtra NEET PG selection list.")
        return

    print(f"Found {len(extracted_data)} records. Creating Excel file...")
    df = pd.DataFrame(extracted_data)
    df['Form No.'] = df['Form No.'].astype(str)
    # Convert SML to numeric; keep decimals for fractional values, integers as int
    df['SML'] = pd.to_numeric(df['SML'], errors='coerce')
    df['SML'] = df['SML'].apply(lambda x: int(x) if pd.notna(x) and x == int(x) else x)
    # Clean up any quota/remark text that bled into the Place column
    df = _clean_bleeding_place(df)
    df = df.sort_values('Sr. No.')

    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='PG_Selection_List', index=False)
        ws = writer.sheets['PG_Selection_List']
        for column in ws.columns:
            max_length = max((len(str(cell.value or '')) for cell in column), default=0)
            ws.column_dimensions[column[0].column_letter].width = min(max_length + 2, 50)

    print(f"✅ Saved to '{excel_path}'")
    print(f"📊 Total records: {len(extracted_data)}")
    print("\n📋 Sample:")
    print(df.head().to_string(index=False))


def main():
    print("=" * 60)
    print("📄 MAHARASHTRA NEET PG SELECTION LIST PARSER")
    print("=" * 60)
    print(f"⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    pdf_files = [f for f in os.listdir('.') if f.lower().endswith('.pdf')]
    if not pdf_files:
        print("❌ No PDF files found in current directory.")
        return

    pdf_filename = max(pdf_files, key=lambda f: os.path.getsize(f)) if len(pdf_files) > 1 else pdf_files[0]
    base_name = os.path.splitext(pdf_filename)[0]
    excel_filename = f"{base_name}_Parsed.xlsx"

    print(f"📂 Input: {pdf_filename}")
    print(f"📊 Output: {excel_filename}\n")

    parse_pg_pdf(pdf_filename, excel_filename)

    print(f"\n⏰ Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    main()

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
    "OPEN", "OBC", "SC", "ST", "EWS", "SEBC", "NTC", "NTB", "NTD", "VJA", "MIN", "PWD"
]


def extract_name_category(text):
    text = text.strip()
    for cat in KNOWN_CATEGORIES:
        if text.endswith(' ' + cat):
            return text[:-len(cat) - 1].strip(), cat
    return text, ""


def parse_right_side(text):
    """Extract college+location, quota, and status markers from the right portion of a data line."""
    text = text.strip()

    # Pull trailing word-based status: Against, Against NRI, NRI (not in parens)
    trailing_text = re.search(r'\s+(Against(?:\s+NRI)?|NRI)\s*$', text)
    trailing = trailing_text.group(1).strip() if trailing_text else ""
    if trailing_text:
        text = text[:trailing_text.start()].strip()

    # Pull trailing parenthesised markers: (Ret.), (EMD), (EMR), (CANC/NJ), etc.
    status_match = re.search(r'((?:\s*\([A-Za-z./ ]+\))+)\s*$', text)
    status = status_match.group(1).strip() if status_match else ""
    if status_match:
        text = text[:status_match.start()].strip()

    # Combine all trailing markers
    all_status = " ".join(filter(None, [status, trailing]))

    # Quota: last token matching a known category, I.Q., NRI, ORPHAN, PH, or EM-prefixed variant
    quota_match = re.search(
        r'\s+((?:PH\s+)?(?:EM)?(?:OPEN|OBC|SC|ST|EWS|SEBC|NTC|NTB|NTD|VJA|MIN)|I\.Q\.|NRI|ORPHAN)\s*$',
        text
    )
    if quota_match:
        quota_base = quota_match.group(1)
        college_loc = text[:quota_match.start()].strip()
    else:
        quota_base = "N/A"
        college_loc = text

    quota = (quota_base + " " + all_status).strip() if all_status else quota_base
    return college_loc, quota


def parse_pg_pdf(pdf_path, excel_path):
    """
    Extracts student selection data from a Maharashtra NEET PG selection list PDF
    and saves it to an Excel file.

    Output columns: Sr. No., SML, Form No., Name, Category, Subject Code, Subject, College, Quota
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
        sml = header_match.group(3)
        form_no = header_match.group(4)
        rest = header_match.group(5).strip()
        rest = rest.strip()

        # --- Choice Not Available ---
        if "Choice Not Available" in rest:
            name_cat = rest.split("Choice Not Available")[0].strip()
            name, category = extract_name_category(name_cat)
            extracted_data.append({
                "Sr. No.": int(sr_no),

                "SML": sml,
                "Form No.": form_no,
                "Name": name,
                "Category": category or "OPEN",
                "Subject Code": "N/A",
                "Subject": "N/A",
                "College": "N/A",
                "Quota": "Choice Not Available"
            })
            continue

        # --- Disqualified ---
        if "Disqualified" in rest:
            name_cat = rest.split("Disqualified")[0].strip()
            name, category = extract_name_category(name_cat)
            disq_reason = "Disqualified" + rest.split("Disqualified", 1)[1].strip()
            extracted_data.append({
                "Sr. No.": int(sr_no),

                "SML": sml,
                "Form No.": form_no,
                "Name": name,
                "Category": category or "OPEN",
                "Subject Code": "N/A",
                "Subject": "N/A",
                "College": "N/A",
                "Quota": disq_reason
            })
            continue

        # --- Normal row: anchor on subject code XXXX[S/I/N] : SUBJECT ---
        # Suffix S=regular, I=in-service, N=NRI
        subj_match = re.search(r'(\d{4}[A-Z])\s*:\s*([A-Z][A-Z\s&/.()\-]+?)(?=\s{2,}|$)', rest)
        if not subj_match:
            continue

        name_cat = rest[:subj_match.start()].strip()
        subj_code = subj_match.group(1)
        subj_name = subj_match.group(2).strip()
        after_subj = rest[subj_match.end():].strip()

        name, category = extract_name_category(name_cat)
        college_loc, quota = parse_right_side(after_subj)

        extracted_data.append({
            "Sr. No.": int(sr_no),
            "SML": sml,
            "Form No.": form_no,
            "Name": name,
            "Category": category or "OPEN",
            "Subject Code": subj_code,
            "Subject": subj_name,
            "College": college_loc,
            "Quota": quota
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

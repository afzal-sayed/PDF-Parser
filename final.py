# Author: Afzal Sayed
# Email:  afzal.sayed04@gmail.com
# GitHub: github.com/afzal-sayed
# LinkedIn: linkedin.com/in/afzal-sayed

import fitz  # PyMuPDF library
import pandas as pd
import re
import os
from datetime import datetime

def parse_student_list_to_excel(pdf_path, excel_path):
    """
    Extracts student selection data from a PDF file and saves it to an Excel file.
    Specifically designed for Maharashtra NEET selection list format.
    
    This script successfully parsed 38,359 records from 1,106 pages.

    Args:
        pdf_path (str): The path to the input PDF file.
        excel_path (str): The path where the output Excel file will be saved.
    """
    # --- 1. Check if PDF file exists ---
    if not os.path.exists(pdf_path):
        print(f"Error: The file '{pdf_path}' was not found.")
        print("Please make sure the PDF file is in the same directory as the script, or provide the full path.")
        return

    print(f"Opening and reading PDF: {pdf_path}...")
    
    # --- 2. Extract text from all pages of the PDF ---
    try:
        doc = fitz.open(pdf_path)
        print(f"PDF has {len(doc)} pages. This may take a few minutes...")
        
        full_text = ""
        processed_pages = 0
        
        for page_num, page in enumerate(doc):
            # Show progress every 100 pages
            if page_num % 100 == 0:
                print(f"Processing page {page_num + 1}/{len(doc)}...")
            
            # Extract text from page
            page_text = page.get_text("text")
            full_text += page_text + "\n"
            processed_pages += 1
            
        doc.close()
        print(f"Successfully processed {processed_pages} pages.")
        
    except Exception as e:
        print(f"An error occurred while reading the PDF file: {e}")
        return

    # --- 3. Parse text line by line for better control ---
    # Based on the header format:
    # Sr. No. | AIR | NEET Roll No. | CET Form No. | Name | G | Cat. | Quota | Code | College
    # Looking for pattern like: number number number number NAME M/F CATEGORY ...
    
    print("Parsing extracted text to find student data...")
    
    # Split text into lines for easier processing
    lines = full_text.split('\n')
    extracted_data = []
    
    # Find data lines (skip headers and other content)
    data_started = False
    
    for line_num, line in enumerate(lines):
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
            
        # Check if we've reached the data section
        # Whitespace-tolerant: column widths vary across selection-list variants
        # (e.g. MBBS/BDS lists pad "Name" wider than AYUSH lists).
        if re.search(r'Sr\.\s+AIR\s+NEET', line) or re.search(r'Roll No\.\s+No\.', line):
            data_started = True
            continue
            
        # Skip header separator lines
        if line.startswith('---') or 'Legends' in line:
            continue
            
        # Skip if data hasn't started yet
        if not data_started:
            continue
            
        # Try to match student data line
        # Pattern: Sr.No Air NeRollNo CETFormNo Name Gender Category QuotaInfo CollegeCode CollegeName
        # Name is greedy, not lazy: some names contain a standalone middle
        # initial ("AMAN M SHARIF SAGRI"), which a lazy match stops at,
        # mistaking the initial for the trailing Gender field.
        match = re.match(r'^\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\$?[A-Z\s.]+)\s+([MF])\s+(.*)', line)

        if match:
            sr_no, air, neet_roll, cet_form, name, gender, rest_of_line = match.groups()

            # Clean up the name; strip $ minority marker if present
            name = name.lstrip('$').strip()
            rest_of_line = rest_of_line.strip()
            
            # Default values
            category = "N/A"
            quota = "N/A"
            earmark = ""
            college_code = "N/A"
            college_name = "N/A"
            course = "N/A"
            city = "N/A"

            # Known reservation-category codes (the "Cat." column) -- NOT
            # quota/seat-type tokens like OPEN, HOPEN, DEF1/2/3, I.Q., EMOBC,
            # which only ever appear in Quota, never Cat. "VJ" is deliberately
            # not listed (unobserved; would wrongly prefix-match "VJA").
            known_categories = [
                "ORP-A", "ORP-B", "ORP-C",
                "SEBC", "SOBC",
                "OBC", "EWS", "NT1", "NT2", "NT3", "VJA", "NTB", "NTC", "NTD",
                "MIN", "PWD", "EBC", "SBC", "MKB", "NRI",
                "HA", "D1", "D2", "D3", "SC", "ST",
            ]

            # Modifier-only flags: they always combine with a base category
            # (or stand alone) but never equal a Quota value themselves, so
            # peeling continues through them even when space-separated from
            # the token before (e.g. "OBC HA", "OBC D1"). Contrast with base
            # codes like OBC/SC/SEBC, which a candidate can also be *allotted
            # a seat under* -- a second, space-separated occurrence of one of
            # those (e.g. "SEBC SEBC") is the Quota field, not a second
            # category flag, and must NOT be peeled again.
            modifier_categories = {"HA", "D1", "D2", "D3", "PWD", "MKB", "NRI", "ORP-A", "ORP-B", "ORP-C"}

            def extract_category_quota(text):
                """
                Split a "Cat. Quota" blob into (category, quota).

                Only tokens in `known_categories` are ever treated as
                category; everything else -- including a lone "OPEN", which
                used to be misclassified as a category -- is quota, even
                when it's the very first word. There is no generic "first
                word as category" fallback: that used to turn e.g.
                "OPEN (W)" (no category, general/open candidate) into
                category "OPEN", quota "(W)" instead of category "", quota
                "OPEN (W)". Multiple category flags are sometimes glued with
                no separating space (e.g. "SEBCHA" = SEBC + HA, "D1HA" after
                a space-separated base like "OBC D1HA") and sometimes fully
                space-separated (e.g. "OBC HA", "OBC D1") -- both are peeled
                into one combined category string, preserving whichever
                separator (or none) the PDF actually used. After crossing a
                space, only a `modifier_categories` token is peeled further
                (e.g. the "HA" in "OBC HA"); a *base* code appearing again
                after a space (e.g. the second "SEBC" in "SEBC SEBC") is the
                Quota field, not a repeated category flag.
                """
                text = text.strip()
                if not text:
                    return "", ""

                category = ""
                remaining = text
                crossed_space = False
                while remaining:
                    matched = next(
                        (cat for cat in known_categories
                         if remaining == cat or remaining.startswith(cat)),
                        None
                    )
                    if not matched:
                        break
                    if crossed_space:
                        if matched not in modifier_categories:
                            break
                        category += " "
                    category += matched
                    remaining = remaining[len(matched):]
                    if not remaining:
                        break
                    if remaining[0] != ' ':
                        crossed_space = False
                        continue  # glued to more letters -- keep peeling
                    remaining = remaining.lstrip()
                    crossed_space = True

                quota_part = re.sub(r'\s+', ' ', remaining).strip()
                return category, quota_part

            def cleanup_quota(quota_str):
                """
                Clean up malformed quota strings from PDF extraction.
                Handles cases like "OPEN (W" (missing closing bracket) -> "OPEN (W)"
                """
                if not quota_str or quota_str == "N/A":
                    return quota_str
                
                # Fix missing closing brackets - e.g., "OPEN (W" -> "OPEN (W)"
                # Match pattern like "(X" where X is a letter and no closing bracket
                quota_str = re.sub(r'\(([A-Za-z])\s*$', r'(\1)', quota_str)
                quota_str = re.sub(r'\(([A-Za-z]{2,})\s*$', r'(\1)', quota_str)  # Multiple letters
                
                # Also handle cases with trailing text after malformed bracket
                # e.g., "OPEN (W EMD" -> "OPEN (W) EMD"
                quota_str = re.sub(r'\(([A-Za-z])\s+', r'(\1) ', quota_str)
                
                # Normalize multiple spaces
                quota_str = re.sub(r'\s+', ' ', quota_str).strip()

                return quota_str

            # Earmark tokens (per the PDF Legends line: EMD = EarMarking Donor,
            # EMR = EarMarking Receiver) plus MINO (minority) and OrphanC (orphan
            # candidate) are distinct from the quota itself and from the "(W)"
            # women's-quota marker, which must stay part of Quota.
            earmark_token_re = re.compile(r'\s*(\(EMD\)|\(EMR\)|MINO|OrphanC)\s*$')

            def extract_earmark(quota_str):
                """
                Peel any trailing earmark tokens off a cleaned-up quota string.
                Returns (quota_without_earmark, earmark) with earmark == "" when
                none are present -- some selection lists never contain one.
                """
                if not quota_str or quota_str == "N/A":
                    return quota_str, ""

                tokens = []
                remaining = quota_str
                while True:
                    m = earmark_token_re.search(remaining)
                    if not m:
                        break
                    tokens.insert(0, m.group(1))
                    remaining = remaining[:m.start()].rstrip()

                return remaining.strip(), " ".join(tokens)

            if "Choice Not Available" in rest_of_line:
                # Handle case where no college is assigned
                parts = rest_of_line.split("Choice Not Available")
                cat, quota_part = extract_category_quota(parts[0].strip()) if parts[0].strip() else ("N/A", "")
                category = cat
                # Clean up quota formatting - normalize multiple spaces
                quota_part = re.sub(r'\s+', ' ', quota_part) if quota_part else ""
                quota_part = cleanup_quota(quota_part) if quota_part else ""
                quota_part, earmark = extract_earmark(quota_part) if quota_part else ("", "")
                quota = (quota_part + " Choice Not Available").strip() if quota_part else "Choice Not Available"
            else:
                # Handle case where college is assigned
                college_match = re.search(r'(\d{4})\s*:\s*(.*?)$', rest_of_line)
                if college_match:
                    college_code = college_match.group(1).strip()
                    college_name = college_match.group(2).strip()
                    before_college = rest_of_line[:college_match.start()].strip()
                    cat, quota_part = extract_category_quota(before_college)
                    category = cat
                    # Clean up quota formatting - normalize multiple spaces and handle (W), (EMD), etc.
                    quota_part = re.sub(r'\s+', ' ', quota_part) if quota_part else ""
                    quota = quota_part if quota_part else "OPEN"
                    quota = cleanup_quota(quota)
                    quota, earmark = extract_earmark(quota)
                    quota = quota or "OPEN"
                    # Strip trailing status markers from college name (e.g. "RAP AC MUMBAI(Ret.)")
                    # and append them to the quota field where they belong.
                    college_status = re.search(r'((?:\([A-Za-z./ ]+\))+)\s*$', college_name)
                    if college_status:
                        suffix = college_status.group(1).strip()
                        college_name = college_name[:college_status.start()].strip()
                        quota = (quota + " " + suffix).strip()
                    # College code range: 1xxx/12xx = Medical College (MBBS),
                    # 2xxx = Dental College (BDS) -- confirmed against Maharashtra
                    # CET Cell code numbering (GMC/MC vs GDC/DC abbreviations).
                    if college_code.startswith("1"):
                        course = "MBBS"
                    elif college_code.startswith("2"):
                        course = "BDS"
                    else:
                        # e.g. 3xxx = AYUSH (BAMS/BHMS/BUMS) colleges -- not
                        # derivable from the code range alone.
                        course = "N/A"
                    city = college_name.split()[-1] if college_name and college_name != "N/A" else "N/A"
                else:
                    # If no college code found, treat entire rest as category/quota
                    cat, quota_part = extract_category_quota(rest_of_line)
                    category = cat
                    # Clean up quota formatting
                    quota_part = re.sub(r'\s+', ' ', quota_part) if quota_part else ""
                    quota = quota_part if quota_part else "OPEN"
                    quota = cleanup_quota(quota)
                    quota, earmark = extract_earmark(quota)
                    quota = quota or "OPEN"
            
            # Append the structured data
            extracted_data.append({
                "Sr. No.": int(sr_no),
                "AIR": int(air),
                "NEET Roll No.": neet_roll,
                "CET Form No.": cet_form,
                "Name": name,
                "Gender": gender,
                "Category": category,
                "Quota": quota,
                "College Code": college_code,
                "College Name": college_name,
                "Earmark": earmark,
                "Course": course,
                "City": city
            })
            
            # Print progress every 1000 records
            if len(extracted_data) % 1000 == 0:
                print(f"Extracted {len(extracted_data)} records so far...")

    # --- 4. Create a DataFrame and save to Excel ---
    if extracted_data:
        print(f"Found {len(extracted_data)} student records. Creating Excel file...")
        df = pd.DataFrame(extracted_data)
        
        # Ensure long numbers are stored as text in Excel to prevent formatting issues
        df['NEET Roll No.'] = df['NEET Roll No.'].astype(str)
        df['CET Form No.'] = df['CET Form No.'].astype(str)
        df['College Code'] = df['College Code'].astype(str)
        
        # Sort by Sr. No. to maintain order
        df = df.sort_values('Sr. No.')
        
        # Save to Excel with proper formatting
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Student_Selection_List', index=False)
            
            # Get the worksheet to apply formatting
            worksheet = writer.sheets['Student_Selection_List']
            
            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)  # Cap at 50 characters
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        print(f"✅ Success! Data has been saved to '{excel_path}'")
        print(f"📊 Total records extracted: {len(extracted_data)}")
        
        # Show some sample data
        print("\n📋 Sample of extracted data:")
        print(df.head().to_string(index=False))
        
    else:
        print("❌ Could not find any matching student data in the PDF.")
        print("This can happen if:")
        print("1. The PDF's text layer is corrupted or has an unexpected format")
        print("2. The data structure is different from expected")
        print("3. The PDF is image-based and needs OCR")

def main():
    """Main function to run the PDF parsing"""
    print("=" * 60)
    print("📄 MAHARASHTRA NEET SELECTION LIST PARSER")
    print("=" * 60)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Find the first PDF file in the current directory
    pdf_files = [f for f in os.listdir('.') if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print(f"❌ Error: No PDF files found in current directory.")
        print("📁 Current directory contents:")
        for file in os.listdir('.'):
            print(f"   - {file}")
        return
    
    # Use the first PDF found, or if multiple, use the largest one (likely to have data)
    if len(pdf_files) > 1:
        pdf_filename = max(pdf_files, key=lambda f: os.path.getsize(f))
        print(f"📁 Multiple PDF files found. Using largest: {pdf_filename}")
    else:
        pdf_filename = pdf_files[0]
    
    # Generate output filename from input filename
    base_name = os.path.splitext(pdf_filename)[0]
    excel_filename = f"{base_name}_Parsed.xlsx"
    
    print(f"📂 Input PDF: {pdf_filename}")
    print(f"📊 Output Excel: {excel_filename}")
    print()
    
    # Run the parsing function
    parse_student_list_to_excel(pdf_filename, excel_filename)
    
    print(f"\n⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

# --- Main execution block ---
if __name__ == "__main__":
    main()

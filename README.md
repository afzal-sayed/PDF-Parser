# Maharashtra NEET Selection List Parser

A web app that parses Maharashtra NEET **UG and PG** selection list PDFs and exports the data as clean, structured Excel files.

Built for the specific formats published by the Maharashtra state authority (SCET Cell / MUHS / ARA) — supports all rounds including stray vacancy rounds.

---

## Features

- Drag-and-drop or browse PDF upload
- Supports both **NEET UG** (AYUSH courses) and **NEET PG** (MD/MS/Diploma) selection lists
- Parses thousands of records in seconds
- Downloads a formatted `.xlsx` file instantly
- Light / dark theme toggle
- Works locally or deployed on Vercel

---

## Output Columns

### UG Parser (`final.py`) — 10 columns
`Sr. No. | AIR | NEET Roll No. | CET Form No. | Name | Gender | Category | Quota | College Code | College Name`

### PG Parser (`parse_pg.py`) — 13 columns
`Sr. No. | SML | I/IB | Form No. | Name | Category | Subject Code | Subject | College | Place | Quota | Remarks | Remarks (Combined)`

---

## Quick Start

### Windows

```bat
install.bat   :: Install dependencies
start.bat     :: Start the server (opens browser automatically)
```

### Linux / macOS

```bash
./install.sh   # Install dependencies
./start.sh     # Start the server (opens browser automatically)
```

Then open **http://127.0.0.1:5000** if the browser doesn't open automatically.

---

## Manual Setup

**Requirements:** Python 3.8+

```bash
pip install -r requirements.txt
```

Create a `.env` file (optional):

```env
MAX_UPLOAD_MB=500
```

Start the server:

```bash
python app.py
```

---

## Run Parsers Standalone

```bash
# Parse a specific PDF directly (no server needed)
python3 -c "
from parse_pg import parse_pg_pdf
parse_pg_pdf('path/to/selection_list.pdf', 'output.xlsx')
"

python3 -c "
from final import parse_student_list_to_excel
parse_student_list_to_excel('path/to/selection_list.pdf', 'output.xlsx')
"
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MAX_UPLOAD_MB` | `500` | Max upload file size in MB. Set to `4` on Vercel (platform limit). |

---

## Deploying to Vercel

1. Install the Vercel CLI: `npm i -g vercel`
2. Set the upload limit env var: `vercel env add MAX_UPLOAD_MB` → enter `4`
3. Deploy: `vercel --prod`

---

## Project Structure

```
parser/
├── api/
│   └── index.py          # Vercel serverless entry point
├── templates/
│   └── index.html        # Frontend UI (drag-and-drop, UG/PG toggle)
├── app.py                # Flask app; /upload dispatches to UG or PG parser
├── final.py              # UG parser (parse_student_list_to_excel)
├── parse_pg.py           # PG parser (parse_pg_pdf)
├── requirements.txt      # Python dependencies
├── vercel.json           # Vercel deployment config
├── install.bat / .sh     # Dependency installer scripts
└── start.bat / .sh       # Server launcher scripts
```

---

## Supported PDF Formats

Text-layer PDFs only — scanned/image-based PDFs are not supported.

### NEET UG (AYUSH courses)
Maharashtra NEET UG selection lists — all rounds (1st through Stray Vacancy):
```
Sr. No. | AIR | NEET Roll No. | CET Form No. | Name | G | Category | Quota | Code | College
```

### NEET PG (MD/MS/Diploma)
Maharashtra NEET PG selection lists — all rounds (1st, 3rd, Stray Vacancy 1 & 2):
```
SrNo | [I-/IB-] | SML | FormNo | Name [Category] | SubjectCode : Subject | College | Place | Quota
```
- `I-` prefix = inservice candidate with incentive marks
- `IB-` prefix = inservice candidate without incentive marks
- Subject code suffix: `S`=regular seat, `I`=in-service seat, `N`=NRI seat

---

## Author

**Afzal Sayed**
- Email: [afzal.sayed04@gmail.com](mailto:afzal.sayed04@gmail.com)
- GitHub: [github.com/afzal-sayed](https://github.com/afzal-sayed)
- LinkedIn: [linkedin.com/in/afzal-sayed](https://linkedin.com/in/afzal-sayed)

---

## License

MIT

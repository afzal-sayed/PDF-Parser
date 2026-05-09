# Maharashtra NEET Selection List Parser

A web app that parses Maharashtra NEET UG selection list PDFs and exports the data as a clean, structured Excel file.

Built for the specific format published by the Maharashtra state authority — extracts all student records including Sr. No., AIR, NEET Roll No., CET Form No., Name, Gender, Category, Quota, College Code, and College Name.

---

## Features

- Drag-and-drop or browse PDF upload
- Parses thousands of records in seconds
- Downloads a formatted `.xlsx` file instantly
- Light / dark theme toggle
- Works locally or deployed on Vercel

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

Create a `.env` file (or copy from the example):

```env
MAX_UPLOAD_MB=500
```

Start the server:

```bash
python app.py        # Linux / macOS
python app.py        # Windows
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

See `.env.vercel` for reference values.

---

## Project Structure

```
parser/
├── api/
│   └── index.py          # Vercel serverless entry point
├── templates/
│   └── index.html        # Frontend UI
├── app.py                # Flask application
├── final.py              # PDF parsing & Excel export logic
├── requirements.txt      # Python dependencies
├── vercel.json           # Vercel deployment config
├── .env                  # Local environment variables
├── .env.vercel           # Vercel env variable reference
├── install.bat / .sh     # Dependency installer scripts
└── start.bat / .sh       # Server launcher scripts
```

---

## Supported PDF Format

Designed for the **Maharashtra NEET UG selection list** format:

```
Sr. No. | AIR | NEET Roll No. | CET Form No. | Name | G | Category | Quota | Code | College
```

Image-based (scanned) PDFs are not supported — the PDF must have a text layer.

---

## Author

**Afzal Sayed**
- Email: [afzal.sayed04@gmail.com](mailto:afzal.sayed04@gmail.com)
- GitHub: [github.com/afzal-sayed](https://github.com/afzal-sayed)
- LinkedIn: [linkedin.com/in/afzal-sayed](https://linkedin.com/in/afzal-sayed)

---

## License

MIT

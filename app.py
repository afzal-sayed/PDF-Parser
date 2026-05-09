# Author: Afzal Sayed
# Email:  afzal.sayed04@gmail.com
# GitHub: github.com/afzal-sayed
# LinkedIn: linkedin.com/in/afzal-sayed

import io
import os
import tempfile
from dotenv import load_dotenv
from flask import Flask, render_template, request, send_file, jsonify
from final import parse_student_list_to_excel

load_dotenv()

app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
)
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_UPLOAD_MB', 500)) * 1024 * 1024


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload():
    if 'pdf' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    pdf_file = request.files['pdf']

    if not pdf_file.filename.lower().endswith('.pdf'):
        return jsonify({'error': 'Please upload a PDF file'}), 400

    with tempfile.TemporaryDirectory() as tmp_dir:
        pdf_path = os.path.join(tmp_dir, pdf_file.filename)
        base_name = os.path.splitext(pdf_file.filename)[0]
        excel_path = os.path.join(tmp_dir, f"{base_name}_Parsed.xlsx")

        pdf_file.save(pdf_path)
        parse_student_list_to_excel(pdf_path, excel_path)

        if not os.path.exists(excel_path):
            return jsonify({'error': 'Parsing failed — no student records found in the PDF'}), 500

        # Read into memory before the temp dir is deleted
        with open(excel_path, 'rb') as f:
            excel_bytes = io.BytesIO(f.read())

    excel_bytes.seek(0)
    return send_file(
        excel_bytes,
        as_attachment=True,
        download_name=f"{base_name}_Parsed.xlsx",
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


if __name__ == '__main__':
    app.run(debug=True)

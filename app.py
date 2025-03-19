from flask import Flask, render_template, request, send_file, jsonify
import os
from PyPDF2 import PdfReader, PdfWriter
import pdfplumber
import tempfile

def split_pdf_by_account_month(input_pdf):
    """
    Splits a multi-account, multi-month PDF into separate PDFs for each account and month,
    and returns a list of temporary file paths.
    """
    reader = PdfReader(input_pdf)
    pdf_texts = []
    
    with pdfplumber.open(input_pdf) as pdf:
        for page in pdf.pages:
            pdf_texts.append(page.extract_text() or "")
    
    split_pdfs = {}
    current_writer = None
    current_key = None
    
    with pdfplumber.open(input_pdf) as pdf:
        for i, page in enumerate(pdf.pages):
            text = pdf_texts[i]
            
            if "Account name" in text and "Transactions from" in text:
                lines = text.split("\n")
                account_name = None
                month_year = None
                
                for j, line in enumerate(lines):
                    if "Account name" in line and j + 1 < len(lines):
                        account_name = lines[j + 1].strip()
                    if "Transactions from" in line:
                        month_year = line.split("from")[-1].strip().replace(",", "").replace(" ", "_")
                
                if account_name and month_year:
                    current_key = f"{account_name}_{month_year}".replace("/", "-")
                    current_writer = PdfWriter()
                    split_pdfs[current_key] = current_writer
            
            if current_writer:
                current_writer.add_page(reader.pages[i])
    
    temp_files = []
    for key, writer in split_pdfs.items():
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        with open(temp_file.name, "wb") as out_file:
            writer.write(out_file)
        temp_files.append(temp_file.name)
    
    return temp_files

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    if "pdfFile" not in request.files:
        return jsonify({"success": False, "message": "No file uploaded"}), 400
    
    file = request.files["pdfFile"]
    if file.filename == "":
        return jsonify({"success": False, "message": "No selected file"}), 400
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_input:
        file.save(temp_input.name)
        split_files = split_pdf_by_account_month(temp_input.name)
    
    if not split_files:
        return jsonify({"success": False, "message": "No files were split"}), 500
    
    first_file = split_files[0]
    return send_file(first_file, as_attachment=True, download_name=os.path.basename(first_file))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
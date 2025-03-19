from flask import Flask, render_template, request, send_file
import os
from PyPDF2 import PdfReader, PdfWriter
import pdfplumber

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def split_pdf_by_account_month(input_pdf, output_dir):
    os.makedirs(output_dir, exist_ok=True)
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

    split_pdf_paths = []
    for key, writer in split_pdfs.items():
        output_path = os.path.join(output_dir, f"{key}.pdf")
        with open(output_path, "wb") as out_file:
            writer.write(out_file)
        split_pdf_paths.append(output_path)

    return split_pdf_paths

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    if "pdfFile" not in request.files:
        return "No file uploaded", 400

    file = request.files["pdfFile"]
    if file.filename == "":
        return "No selected file", 400

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    split_files = split_pdf_by_account_month(file_path, OUTPUT_FOLDER)

    return f"PDF split successfully! Download {len(split_files)} files from the 'outputs' folder."

@app.route("/download/<filename>")
def download(filename):
    return send_file(os.path.join(OUTPUT_FOLDER, filename), as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

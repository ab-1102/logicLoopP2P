# 🔒 AI Document Redactor

An interactive, secure web application built with **Streamlit** and **PyMuPDF** designed to automatically detect Personally Identifiable Information (PII) in PDF documents, preview redactions, and export fully sanitized and verified PDFs.

---

## 🚀 Key Features

* **Automated PII Detection:** Scans PDF text layers using robust regular expressions to identify sensitive data types:
  * **Emails**
  * **Phone Numbers** (+91 and standard formats)
  * **Aadhaar Numbers**
  * **PAN Card Numbers**
  * **PIN Codes**
* **Interactive Document Viewer:** Switch between the original document view and a live redaction preview mode.
* **Streamlined Redaction Panel:** View all detected PII grouped by page with automatic black-box redaction mapping.
* **Cryptographic & Structural Verification:** Automatically verifies exported PDF files to ensure:
  * No extractable text layers remain.
  * Sensitive user metadata is completely wiped.
  * No hidden annotations or comments are left behind.
* **Secure Export:** Download your sanitized, redacted PDF instantly.

---

## 🛠️ Tech Stack

* **Python** (3.8+)
* **Streamlit** (Interactive User Interface)
* **PyMuPDF (`fitz`)** (PDF parsing, text extraction, rendering, and rebuilding)
* **Pillow (`PIL`)** (Image manipulation and redaction drawing)

---

## ⚙️ Installation & Setup

### 1. Prerequisites
Ensure you have Python installed on your system.

### 2. Install Dependencies
Install the required Python packages using `pip`:

```bash
pip install streamlit pymupdf pillow
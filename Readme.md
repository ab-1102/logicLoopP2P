# 🔒 AI Document Redactor

An interactive, web application built with **Streamlit** and **PyMuPDF** designed to automatically detect Personally Identifiable Information (PII) in PDF documents, preview redactions, and export fully sanitized and verified PDFs.

---

## 🚀 Key Features

* **Automated PII Detection:** Scans PDF text layers using robust regular expressions to identify sensitive data types:
  * **Emails**
  * **Phone Numbers** (+91 and standard formats)
  * **Aadhaar Numbers**
  * **PAN Card Numbers**
  * **PIN Codes**
* **Interactive Document Viewer:** Switch between the original document view and a live redaction preview mode.

---

## 🛠️ Tech Stack

* **Python** (3.8+)
* **Streamlit** (Interactive User Interface)
* **PyMuPDF (`fitz`)** (PDF parsing, text extraction, rendering, and rebuilding)
* **Pillow (`PIL`)** (Image manipulation and redaction drawing)
* **PII Identification & Mapping Logic:**
  * **Granular Word Extraction:** The engine extracts all words from the PDF page along with their exact coordinate bounding boxes (`fitz` word tuples).
  * **Sequential Text Reconstruction:** It maps these words into a continuous, indexed string (`PDFWord` data structures with `start` and `end` character tracking) to preserve layout context.
  * **Regex Pattern Matching:** Regular expressions (`re`) scan the reconstructed text for sensitive entities (Emails, Phone numbers, PAN, Aadhaar, PIN codes).
  * **Coordinate Projection (`bbox_for_text`):** When a regex match is found, its character start and end indices are mapped back to the corresponding word tokens. This dynamically computes the exact bounding coordinates (`x1, y1, x2, y2`) of the target text, ensuring that redactions target only the sensitive data rather than entire lines or paragraphs.

---

### Future Scope
* **Advanced NLP/NER Integration:** Incorporate machine learning-based Named Entity Recognition (NER) models (such as spaCy or Microsoft Presidio) to detect contextual PII like names, medical terms, and physical addresses.
* **Multi-Format Support:** Extend support beyond PDFs to handle Word documents (`.docx`), text files, and image-based scans using integrated Optical Character Recognition (OCR).
* **Batch Processing:** Enable multi-file uploads and batch processing capabilities for high-volume enterprise document sanitization.
* **Custom Rule Builder:** Allow users to create, save, and apply custom regular expression templates tailored to specific organizational compliance needs.

---

## ⚙️ Installation & Setup

### 1. Prerequisites
Ensure you have Python installed on your system.

### 2. Install Dependencies
Install the required Python packages using `pip`:

```bash
pip install streamlit pymupdf pillow
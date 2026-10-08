from __future__ import annotations

import io
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw
import streamlit as st

# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="AI Document Redactor",
    page_icon="🔒",
    layout="wide",
)


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class PDFWord:
    text: str
    bbox: tuple[int, int, int, int]
    confidence: float
    start: int
    end: int


@dataclass
class Detection:
    page: int
    text: str
    bbox: tuple[int, int, int, int]
    entity_type: str
    confidence: float
    source: str
    selected: bool = True


@dataclass
class Page:
    number: int
    width: int
    height: int
    words: list[PDFWord]


# ============================================================
# REGEX PATTERNS
# ============================================================

REGEX_PATTERNS = {
    "EMAIL": re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
    ),
    "PHONE": re.compile(
        r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)"
    ),
    "AADHAAR": re.compile(
        r"(?<!\d)\d{4}[\s-]\d{4}[\s-]\d{4}(?!\d)"
    ),
    "PAN": re.compile(
        r"\b[A-Z]{5}\d{4}[A-Z]\b"
    ),
    "PINCODE": re.compile(
        r"(?<!\d)[1-9]\d{5}(?!\d)"
    ),
}


# ============================================================
# REDACTION ENGINE
# ============================================================

class RedactionEngine:
    RENDER_SCALE = 2.0

    def __init__(self) -> None:
        self.pages: list[Page] = []
        self.detections: list[Detection] = []
        self.document_path: Path | None = None

    def load_document(self, path: str | Path) -> None:
        path = Path(path)
        if path.suffix.lower() != ".pdf":
            raise ValueError("Supports PDF files only.")

        if not path.exists():
            raise FileNotFoundError(f"File does not exist: {path}")

        self.pages.clear()
        self.detections.clear()
        self.document_path = path

        document = pymupdf.open(path)
        try:
            if document.page_count == 0:
                raise ValueError("The PDF contains no pages.")

            for page_number in range(document.page_count):
                pdf_page = document[page_number]
                page_words = self._extract_page_words(pdf_page)

                if not page_words:
                    raise ValueError(
                        f"Page {page_number + 1} does not contain an extractable text layer."
                    )

                rect = pdf_page.rect
                width = int(rect.width * self.RENDER_SCALE)
                height = int(rect.height * self.RENDER_SCALE)

                self.pages.append(
                    Page(
                        number=page_number,
                        width=width,
                        height=height,
                        words=page_words,
                    )
                )
        finally:
            document.close()

    def _extract_page_words(self, pdf_page: pymupdf.Page) -> list[PDFWord]:
        raw_words = pdf_page.get_text("words")
        words: list[PDFWord] = []
        current_position = 0

        for raw_word in raw_words:
            x0, y0, x1, y1, text = raw_word[:5]
            text = str(text).strip()
            if not text:
                continue

            bbox = (
                int(x0 * self.RENDER_SCALE),
                int(y0 * self.RENDER_SCALE),
                int(x1 * self.RENDER_SCALE),
                int(y1 * self.RENDER_SCALE),
            )

            start = current_position
            end = start + len(text)

            words.append(
                PDFWord(
                    text=text,
                    bbox=bbox,
                    confidence=1.0,
                    start=start,
                    end=end,
                )
            )
            current_position = end + 1

        return words

    def analyze(self) -> None:
        self.detections.clear()
        for page in self.pages:
            self._detect_page(page)

        # Global deduplication: ensures absolute zero duplicates across the entire list
        seen = set()
        unique_detections = []
        for d in self.detections:
            identifier = (d.page, d.entity_type, d.text, d.bbox)
            if identifier not in seen:
                seen.add(identifier)
                unique_detections.append(d)
        self.detections = unique_detections

    @staticmethod
    def page_text(page: Page) -> str:
        return " ".join(word.text for word in page.words)

    @staticmethod
    def bbox_for_text(
            page: Page,
            start: int,
            end: int,
    ) -> tuple[int, int, int, int] | None:
        matching_words: list[PDFWord] = []

        for word in page.words:
            if word.end <= start:
                continue
            if word.start >= end:
                continue
            matching_words.append(word)

        if not matching_words:
            return None

        x1 = min(word.bbox[0] for word in matching_words)
        y1 = min(word.bbox[1] for word in matching_words)
        x2 = max(word.bbox[2] for word in matching_words)
        y2 = max(word.bbox[3] for word in matching_words)

        return (x1, y1, x2, y2)

    def _detect_page(self, page: Page) -> None:
        text = self.page_text(page)
        if not text.strip():
            return

        for entity_type, pattern in REGEX_PATTERNS.items():
            matches = pattern.finditer(text)
            for match in matches:
                bbox = self.bbox_for_text(page, match.start(), match.end())
                if bbox is None:
                    continue

                self.detections.append(
                    Detection(
                        page=page.number,
                        text=match.group(),
                        bbox=bbox,
                        entity_type=entity_type,
                        confidence=1.0,
                        source="Regex",
                    )
                )

    def get_page_detections(self, page_number: int) -> list[Detection]:
        return [d for d in self.detections if d.page == page_number]

    def render_page(self, page_number: int) -> Image.Image:
        if self.document_path is None:
            raise RuntimeError("No document is loaded.")

        document = pymupdf.open(self.document_path)
        try:
            pdf_page = document[page_number]
            pixmap = pdf_page.get_pixmap(
                matrix=pymupdf.Matrix(self.RENDER_SCALE, self.RENDER_SCALE),
                alpha=False,
            )
            return Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
        finally:
            document.close()

    def redacted_page(self, page_number: int) -> Image.Image:
        image = self.render_page(page_number)
        draw = ImageDraw.Draw(image)
        detections = self.get_page_detections(page_number)

        for detection in detections:
            if not detection.selected:
                continue
            x1, y1, x2, y2 = detection.bbox
            draw.rectangle([x1, y1, x2, y2], fill="black")

        return image

    def export_pdf_bytes(self) -> bytes:
        if not self.pages:
            raise RuntimeError("No document is loaded.")

        output_document = pymupdf.open()
        try:
            for page_number in range(len(self.pages)):
                image = self.redacted_page(page_number)
                buffer = io.BytesIO()
                image.save(buffer, format="PNG")
                image_bytes = buffer.getvalue()

                output_page = output_document.new_page(
                    width=image.width, height=image.height
                )
                output_page.insert_image(output_page.rect, stream=image_bytes)

            output_document.set_metadata({})
            return output_document.tobytes(garbage=4, deflate=True)
        finally:
            output_document.close()

    def verify_pdf_bytes(self, pdf_bytes: bytes) -> tuple[bool, list[str]]:
        problems: list[str] = []

        try:
            document = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        except Exception as exc:
            return False, [f"Could not open output PDF bytes: {exc}"]

        try:
            for page_number, page in enumerate(document):
                if page.get_text().strip():
                    problems.append(f"Page {page_number + 1} contains extractable text.")

            # Ignore standard library and system-generated metadata keys
            ignored_keys = ("format", "encryption", "producer", "creator", "trapped", "modDate", "creationDate")
            for key, value in (document.metadata or {}).items():
                if key not in ignored_keys and value:
                    problems.append(f"Metadata field '{key}' is not empty.")

            for page_number, page in enumerate(document):
                if page.annots() is not None:
                    for _ in page.annots():
                        problems.append(f"Page {page_number + 1} contains an annotation.")
        finally:
            document.close()

        return len(problems) == 0, problems


# ============================================================
# STREAMLIT USER INTERFACE
# ============================================================

def main():
    st.title("🔒 AI Document Redactor")
    st.markdown("Upload a PDF document to automatically detect PII, preview redactions, and export securely.")

    # Initialize Engine in Session State
    if "engine" not in st.session_state:
        st.session_state.engine = RedactionEngine()

    engine: RedactionEngine = st.session_state.engine

    # --- Sidebar Controls ---
    st.sidebar.header("Document Control")
    uploaded_file = st.sidebar.file_uploader("Upload PDF", type=["pdf"])

    if uploaded_file is not None:
        if "loaded_file_name" not in st.session_state or st.session_state.loaded_file_name != uploaded_file.name:
            temp_dir = tempfile.TemporaryDirectory()
            st.session_state.temp_dir = temp_dir
            temp_path = Path(temp_dir.name) / uploaded_file.name
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            try:
                engine.load_document(temp_path)
                st.session_state.loaded_file_name = uploaded_file.name
                st.sidebar.success(f"Loaded {len(engine.pages)} page(s).")
            except Exception as e:
                st.sidebar.error(str(e))

    # Analyze Button
    if engine.pages and st.sidebar.button("🔍 Analyze Document"):
        with st.spinner("Analyzing document for PII..."):
            engine.analyze()
            st.sidebar.success(f"Found {len(engine.detections)} PII item(s).")

    # --- Main Application Area ---
    if not engine.pages:
        st.info("👈 Please upload a PDF document using the sidebar to begin.")
        return

    # Page Selection
    page_numbers = [f"Page {i + 1}" for i in range(len(engine.pages))]
    selected_page_label = st.selectbox("Select Page", page_numbers)
    current_page_idx = page_numbers.index(selected_page_label)

    # Layout Columns: Viewer vs Detected PII Panel
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Document Viewer & Preview")
        preview_mode = st.checkbox("Preview Redaction Mode", value=False)

        if preview_mode:
            img = engine.redacted_page(current_page_idx)
            st.image(img, caption=f"Redacted Preview - Page {current_page_idx + 1}", width="stretch")
        else:
            img = engine.render_page(current_page_idx)
            st.image(img, caption=f"Original Page {current_page_idx + 1}", width="stretch")

    with col2:
        st.subheader("Detected PII Panel")
        page_detections = engine.get_page_detections(current_page_idx)

        if not page_detections:
            st.markdown(
                "*No analysis run yet or no PII found on this page. Click **Analyze Document** in the sidebar.*")
        else:
            for detection in page_detections:
                detection.selected = True  # Automatically selected for redaction
                st.markdown(f"- **{detection.entity_type}**: `{detection.text}`")

    # --- Export Section ---
    st.markdown("---")
    st.subheader("Export Sanitized PDF")

    if st.button("🚀 Generate & Verify Sanitized PDF"):
        if not engine.detections:
            st.warning("Please analyze the document first.")
        else:
            try:
                pdf_bytes = engine.export_pdf_bytes()
                passed, problems = engine.verify_pdf_bytes(pdf_bytes)

                if passed:
                    st.success("✅ PDF created successfully and verified securely!")
                    st.download_button(
                        label="📥 Download Sanitized PDF",
                        data=pdf_bytes,
                        file_name="sanitized_output.pdf",
                        mime="application/pdf"
                    )
                else:
                    st.error("❌ Verification failed:")
                    for prob in problems:
                        st.write(f"- {prob}")
            except Exception as e:
                st.error(f"Export error: {str(e)}")


if __name__ == "__main__":
    main()
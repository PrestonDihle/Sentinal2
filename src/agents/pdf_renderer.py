"""
SENTINEL2 — PDF Renderer
Converts HTML reports to PDF using xhtml2pdf.
"""

import logging
from pathlib import Path
from typing import Optional

from xhtml2pdf import pisa

from src.utils.config import get_reports_dir

logger = logging.getLogger("sentinel2.pdf_renderer")


def html_to_pdf(html_path: str, pdf_path: Optional[str] = None) -> Optional[str]:
    """
    Convert an HTML report file to PDF.

    Args:
        html_path: Path to HTML file
        pdf_path: Optional output path. If None, replaces .html with .pdf

    Returns:
        Path to generated PDF, or None on failure.
    """
    html_path = Path(html_path)
    if not html_path.exists():
        logger.error(f"HTML file not found: {html_path}")
        return None

    if pdf_path is None:
        pdf_path = html_path.with_suffix(".pdf")
    else:
        pdf_path = Path(pdf_path)

    html_content = html_path.read_text(encoding="utf-8")
    return render_html_to_pdf(html_content, str(pdf_path))


def render_html_to_pdf(html_content: str, output_path: str) -> Optional[str]:
    """
    Render HTML string to a PDF file.

    Args:
        html_content: HTML string
        output_path: Path for the output PDF

    Returns:
        Path to generated PDF, or None on failure.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(output_path, "wb") as pdf_file:
            status = pisa.CreatePDF(html_content, dest=pdf_file)

        if status.err:
            logger.error(f"PDF generation had errors: {status.err}")
            return None

        size_kb = output_path.stat().st_size // 1024
        logger.info(f"PDF generated: {output_path} ({size_kb} KB)")
        return str(output_path)

    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        return None


def render_daily_report(run_date: str) -> Optional[str]:
    """Render the daily report HTML to PDF."""
    reports_dir = get_reports_dir()
    html_path = reports_dir / f"sentinel2_daily_{run_date}.html"
    if not html_path.exists():
        logger.error(f"Daily report HTML not found: {html_path}")
        return None
    return html_to_pdf(str(html_path))


def render_black_swan_report(html_path: str) -> Optional[str]:
    """Render a Black Swan alert HTML to PDF."""
    return html_to_pdf(html_path)

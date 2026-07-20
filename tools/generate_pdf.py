from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

def md_to_pdf(md_path, pdf_path):
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter
    margin = 40
    y = height - margin
    c.setFont('Helvetica', 12)

    for line in lines:
        text = line.rstrip('\n')
        if not text:
            y -= 12
            continue
        # Simple wrapping
        if len(text) > 95:
            parts = [text[i:i+95] for i in range(0, len(text), 95)]
        else:
            parts = [text]
        for part in parts:
            if y < margin + 20:
                c.showPage()
                y = height - margin
                c.setFont('Helvetica', 12)
            c.drawString(margin, y, part)
            y -= 14

    c.save()

if __name__ == '__main__':
    root = os.path.dirname(os.path.dirname(__file__))
    md = os.path.join(root, 'README_CHEATSHEET.md')
    pdf = os.path.join(root, 'README_CHEATSHEET.pdf')
    md_to_pdf(md, pdf)
    print('Generated', pdf)

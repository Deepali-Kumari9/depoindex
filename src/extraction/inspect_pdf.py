import fitz

PDF_PATH = "data/Persis_Yu_Deposition_Problem_statement.pdf"

doc = fitz.open(PDF_PATH)

print("Total PDF pages:", len(doc))
print("=" * 60)

for pdf_page in range(min(10, len(doc))):
    page = doc[pdf_page]

    print(f"\nPDF PAGE INDEX: {pdf_page}")
    print("-" * 60)

    text = page.get_text("text", sort=True)

    print(text[:3000])
import fitz
import sys

doc = fitz.open(sys.argv[1])
with open(sys.argv[1].replace(".pdf", ".txt"), "w", encoding="utf-8") as f:
    for page in doc:
        text = page.get_text("text")  # força modo layout simples e seguro
        f.write(text)
        f.write("\n===PAGINA===\n")

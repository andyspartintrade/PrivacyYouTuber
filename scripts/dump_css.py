"""
Εξάγει το CSS του pagination ΑΠΟ ΤΟ ΑΡΧΕΙΟ και το τυπώνει,
για να δω ΤΙ ΑΚΡΙΒΩΣ έχει (όχι τι νομίζω).
"""
import re

h = open("web/index.html", encoding="utf-8").read()

# βρες όλους τους κανόνες που περιέχουν tag-pop / pop-page / pop-pager
print("=== ΟΛΟΙ ΟΙ ΚΑΝΟΝΕΣ ΓΙΑ ΤΟ PAGINATION ===")
for m in re.finditer(r"([^{}]*\{[^{}]*\})", h):
    block = m.group(1)
    if any(k in block for k in ("pop-page-grid", "pop-pager", "tag-pop-list.paged", "tag-pop.paged")):
        print(block.strip())
        print("-" * 50)

print()
print("=== ΠΡΟΣΟΧΗ: υπάρχουν ΔΙΠΛΟΙ κανόνες για .pop-page-grid; ===")
n = len(re.findall(r"\.pop-page-grid\s*\{", h))
print(f"φορές: {n}")

print()
print("=== ΤΟ HTML που παράγει η renderCatPopList (από τον κώδικα) ===")
# βρες τη renderCatPopList και τύπωσε το template
m = re.search(r"function renderCatPopList.*?\n\}", h, re.S)
if m:
    print(m.group(0)[:1500])

"""
Έλεγχος ότι το index.html φορτώνει σωστά + τα i18n keys που χρησιμοποιούνται
υπάρχουν ΟΛΑ στο i18n.json (δεν θα βγει «msg.foo» αντί για κείμενο).
"""
import re, json, os

h = open("web/index.html", encoding="utf-8").read()
d = json.load(open("web/i18n.json", encoding="utf-8"))

# 1) Όλα τα data-i18n* keys
used = set()
used |= set(re.findall(r'data-i18n="([^"]+)"', h))
used |= set(re.findall(r"data-i18n-placeholder=\"([^\"]+)\"", h))
used |= set(re.findall(r'data-i18n-title="([^"]+)"', h))
# 2) t('key') κλήσεις
used |= set(re.findall(r"t\('([^']+)'\)", h))

missing = sorted(k for k in used if k not in d)
print(f"Keys που χρησιμοποιούνται: {len(used)}")
print(f"Keys στο i18n.json:        {len(d)}")
print(f"ΛΕΙΠΟΥΝ:                   {len(missing)}")
for k in missing:
    print("   ❌", k)

# 3) keys στο json που δεν χρησιμοποιούνται (πληροφοριακά)
unused = sorted(k for k in d if k not in used)
print(f"\nΑχρησιμοποίητα keys: {len(unused)} (φυσιολογικό, είναι Διαθέσιμα)")

# 4) Κάθε key έχει en + el;
bad = [k for k, v in d.items() if "en" not in v or "el" not in v]
print(f"Keys χωρίς en/el: {len(bad)}")
for k in bad[:10]:
    print("   ⚠️", k, d[k])

import os
import requests

DOCUMENTS_DIR = "documents"
os.makedirs(DOCUMENTS_DIR, exist_ok=True)

docs = [
    ("01_asu_catalog_2021-2023.pdf",       "https://www.alasu.edu/_qa/2021-2023%20Undergraduate%20Catalog.pdf"),
    ("02_asu_catalog_2019-2021.pdf",       "https://www.alasu.edu/_qa/ASU%202019_2021%20FINAL%20CATALOG_MAIN%202.pdf"),
    ("03_asu_criminal_justice_guide.pdf",  "https://www.alasu.edu/_qa/Curriculum%20Guide%20Approved%202023_0.pdf"),
    ("04_asu_management_guide.pdf",        "https://www.alasu.edu/academics/programs-majors/coba/management-curriculum.pdf"),
    ("05_asu_theatre_ba.pdf",              "https://www.alasu.edu/_qa/Theatre%20BA%20Curriculum%20Sheet.pdf"),
    ("06_asu_grad_catalog.pdf",            "https://www.alasu.edu/_qa/Grad_Catalog-1.pdf"),
    ("07_asu_catalog_2017-2019.pdf",       "https://www.alasu.edu/_qa/2017-19%20Undergraduate%20Catalog%20%20-1-updated_0.pdf"),
    ("08_asu_computer_science_guide.pdf",  "https://www.alasu.edu/websites/Computer%20Science%20Curriculum.pdf"),
    ("09_asu_mathematics_bs.pdf",          "https://www.alasu.edu/_qa/CSTEM%20Mathematics%20B.S..pdf"),
    ("10_asu_biology_prehealth.pdf",       "https://www.alasu.edu/_qa/Biology%20Pre-Health%20Sequence.pdf"),
    ("11_asu_accounting_guide.pdf",        "https://www.alasu.edu/academics/programs-majors/coba/management-curriculum.pdf"),
]

headers = {"User-Agent": "Mozilla/5.0"}

for filename, url in docs:
    dest = os.path.join(DOCUMENTS_DIR, filename)
    print(f"Downloading {filename} ...", end=" ", flush=True)
    try:
        r = requests.get(url, headers=headers, timeout=60)
        r.raise_for_status()
        with open(dest, "wb") as f:
            f.write(r.content)
        size_kb = len(r.content) // 1024
        print(f"OK ({size_kb} KB)")
    except Exception as e:
        print(f"FAILED — {e}")

print("\nDone. Files in ./documents/:")
for f in sorted(os.listdir(DOCUMENTS_DIR)):
    path = os.path.join(DOCUMENTS_DIR, f)
    print(f"  {f}  ({os.path.getsize(path) // 1024} KB)")

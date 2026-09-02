import base64
import json
import subprocess
from pathlib import Path

pdf_path = Path("test.pdf")

content = base64.b64encode(
    pdf_path.read_bytes()
).decode("ascii")

request = {
    "fileName": pdf_path.name,
    "mimeType": "application/pdf",
    "language": "fra",
    "enhanceImage": True,
    "contentBase64": content
}

for psm in [3, 4, 6, 11]:

    print()
    print("=" * 60)
    print(f"TEST PSM {psm}")
    print("=" * 60)

    # On ajoute le PSM dans la requête
    request["psm"] = psm

    process = subprocess.run(
        [
            r".\.venv\Scripts\python.exe",
            "main.py"
        ],
        input=json.dumps(request, ensure_ascii=False),
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace"
    )

    print(process.stdout)

    if process.stderr:
        print("ERREUR:")
        print(process.stderr)

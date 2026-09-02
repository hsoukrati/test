import base64
import json
import subprocess
from pathlib import Path

pdf_path = Path("test.pdf")

if not pdf_path.exists():
    print(f"ERREUR : {pdf_path} introuvable")
    raise SystemExit(1)

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

print("========== RESULTAT ==========")
print(process.stdout)

print("========== ERREUR ==========")
print(process.stderr)

print("========== CODE ==========")
print(process.returncode)

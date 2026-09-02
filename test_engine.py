import base64
import json
import subprocess
from pathlib import Path

# Image à tester
image_path = Path("test.png")

# Conversion image -> Base64
content = base64.b64encode(
    image_path.read_bytes()
).decode("utf-8")

# JSON envoyé à main.py
request = {
    "fileName": image_path.name,
    "mimeType": "image/png",
    "language": "fra",
    "enhanceImage": True,
    "contentBase64": content
}

# Lancement du moteur OCR
process = subprocess.run(
    [
        r"C:\Users\HP\.local\bin\python3.14.exe",
        "main.py"
    ],
    input=json.dumps(request),
    text=True,
    capture_output=True
)

print("========== RESULTAT ==========")
print(process.stdout)

print("========== ERREUR ==========")
print(process.stderr)

print("========== CODE ==========")
print(process.returncode)

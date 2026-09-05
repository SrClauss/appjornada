import re

file_path = "backend/app/routers/ocr.py"
with open(file_path, "r") as f:
    content = f.read()

content = content.replace(
    'modelos = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"]',
    'modelos = ["gemini-1.5-flash", "gemini-1.5-flash-8b", "gemini-1.5-pro"]'
)

with open(file_path, "w") as f:
    f.write(content)
print("Patched models in backend.")

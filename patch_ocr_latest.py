import re

file_path = "backend/app/routers/ocr.py"
with open(file_path, "r") as f:
    content = f.read()

# Fix models list
old_models = 'modelos = ["gemini-1.5-flash", "gemini-1.5-flash-8b", "gemini-1.5-pro"]'
new_models = 'modelos = ["gemini-flash-latest", "gemini-flash-lite-latest", "gemini-pro-latest"]'
content = content.replace(old_models, new_models)

# If it was the 3.6 models before
old_models_2 = 'modelos = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite"]'
content = content.replace(old_models_2, new_models)

# Fix timeout
content = content.replace('timeout=60', 'timeout=180')

with open(file_path, "w") as f:
    f.write(content)
print("Patched models and timeout in backend.")

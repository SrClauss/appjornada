import re

file_path = "app_motorista/lib/screens/ai_terminal_console_screen.dart"
with open(file_path, "r") as f:
    content = f.read()

content = content.replace('gemini-3.5-flash-lite', 'gemini-flash-latest')
content = content.replace('Gemini 3.6', 'Gemini Flash')

with open(file_path, "w") as f:
    f.write(content)
print("Patched frontend logs.")

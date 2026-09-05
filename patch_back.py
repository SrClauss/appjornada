import re

file_path = "app_motorista/lib/main.dart"
with open(file_path, "r") as f:
    content = f.read()

old_back = """  void _onTrilhoBack() {
    setState(() {
      if (_trilhoStep == 'veiculo') {
        _trilhoStep = 'auditoria';
      } else if (_trilhoStep == 'vistoria') {"""

new_back = """  void _onTrilhoBack() {
    setState(() {
      if (_trilhoStep == 'vistoria') {"""

content = content.replace(old_back, new_back)

with open(file_path, "w") as f:
    f.write(content)
print("Patched main.dart back button")

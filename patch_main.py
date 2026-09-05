import re

file_path = "app_motorista/lib/main.dart"
with open(file_path, "r") as f:
    content = f.read()

# Change _trilhoStep defaults
content = content.replace("_trilhoStep = 'auditoria';", "_trilhoStep = 'veiculo';")

with open(file_path, "w") as f:
    f.write(content)
print("Patched main.dart default trilhoStep")

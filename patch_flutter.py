import re

file_path = "app_motorista/lib/screens/fechamento_wizard_screen.dart"
with open(file_path, "r") as f:
    content = f.read()

# I want to make sure the user knows to click the bubble instead of a generic "Gravação de tela iniciada".
# So when they click "GRAVAR TELA", they get a message saying "Clique na bolotinha flutuante para iniciar a gravação"
content = content.replace(
    "setState(() => _isRecording = true);",
    "setState(() => _isRecording = true);\n                                ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Bolinha flutuante ativada! Clique no ícone nela para iniciar a gravação.')));"
)

with open(file_path, "w") as f:
    f.write(content)

print("FechamentoWizardScreen patched.")

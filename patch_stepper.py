import re

file_path = "app_motorista/lib/widgets/stepper_layout.dart"
with open(file_path, "r") as f:
    content = f.read()

# Replace steps 1, 2, 3, 4 with 1, 2, 3
old_steps = """                  _buildStepDot(1, 'Auditoria', currentIdx >= 0),
                  _buildLine(currentIdx >= 1),
                  _buildStepDot(2, 'Veículo', currentIdx >= 1),
                  _buildLine(currentIdx >= 2),
                  _buildStepDot(3, 'Vistoria', currentIdx >= 2),
                  _buildLine(currentIdx >= 3),
                  _buildStepDot(4, 'KM & Hodôm.', currentIdx >= 3),"""

new_steps = """                  _buildStepDot(1, 'Veículo', currentIdx >= 0),
                  _buildLine(currentIdx >= 1),
                  _buildStepDot(2, 'Vistoria', currentIdx >= 1),
                  _buildLine(currentIdx >= 2),
                  _buildStepDot(3, 'KM & Hodôm.', currentIdx >= 2),"""

content = content.replace(old_steps, new_steps)

with open(file_path, "w") as f:
    f.write(content)
print("Patched stepper_layout")

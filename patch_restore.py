import re

stepper_path = "app_motorista/lib/widgets/stepper_layout.dart"
with open(stepper_path, "r") as f:
    stepper = f.read()

# Restore the 4 steps, but name the first one 'Pendências'
old_stepper = """                  _buildStepDot(1, 'Veículo', currentIdx >= 0),
                  _buildLine(currentIdx >= 1),
                  _buildStepDot(2, 'Vistoria', currentIdx >= 1),
                  _buildLine(currentIdx >= 2),
                  _buildStepDot(3, 'KM & Hodôm.', currentIdx >= 2),"""

new_stepper = """                  _buildStepDot(1, 'Pendências', currentIdx >= 0),
                  _buildLine(currentIdx >= 1),
                  _buildStepDot(2, 'Veículo', currentIdx >= 1),
                  _buildLine(currentIdx >= 2),
                  _buildStepDot(3, 'Vistoria', currentIdx >= 2),
                  _buildLine(currentIdx >= 3),
                  _buildStepDot(4, 'KM & Hodôm.', currentIdx >= 3),"""

stepper = stepper.replace(old_stepper, new_stepper)
with open(stepper_path, "w") as f:
    f.write(stepper)

main_path = "app_motorista/lib/main.dart"
with open(main_path, "r") as f:
    main_code = f.read()

# Restore _trilhoStep defaults
main_code = main_code.replace("_trilhoStep = 'veiculo';", "_trilhoStep = 'auditoria';")

# Restore _onTrilhoBack
old_back = """  void _onTrilhoBack() {
    setState(() {
      if (_trilhoStep == 'vistoria') {"""
new_back = """  void _onTrilhoBack() {
    setState(() {
      if (_trilhoStep == 'veiculo') {
        _trilhoStep = 'auditoria';
      } else if (_trilhoStep == 'vistoria') {"""

main_code = main_code.replace(old_back, new_back)
with open(main_path, "w") as f:
    f.write(main_code)

print("Restored and fixed!")

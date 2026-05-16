String? validateRequired(String? value, [String fieldName = 'Campo']) {
  if (value == null || value.trim().isEmpty) return '$fieldName é obrigatório';
  return null;
}

String? validateEmail(String? value) {
  if (value == null || value.trim().isEmpty) return 'E-mail é obrigatório';
  if (!RegExp(r'^[^@]+@[^@]+\.[^@]+').hasMatch(value.trim())) {
    return 'E-mail inválido';
  }
  return null;
}

String? validatePin(String? value) {
  if (value == null || value.isEmpty) return 'PIN é obrigatório';
  if (value.length != 4) return 'O PIN deve ter 4 dígitos';
  if (!RegExp(r'^\d{4}$').hasMatch(value)) return 'PIN deve conter apenas números';
  return null;
}

String? validatePositiveNumber(String? value, [String fieldName = 'Valor']) {
  if (value == null || value.trim().isEmpty) return '$fieldName é obrigatório';
  final n = double.tryParse(value.replaceAll(',', '.'));
  if (n == null) return '$fieldName inválido';
  if (n <= 0) return '$fieldName deve ser maior que zero';
  return null;
}

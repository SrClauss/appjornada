class ApiException implements Exception {
  final int statusCode;
  final String message;

  const ApiException({required this.statusCode, required this.message});

  factory ApiException.fromStatusCode(int statusCode, [String? detail]) {
    switch (statusCode) {
      case 401:
        return ApiException(statusCode: statusCode, message: detail ?? 'Sessão expirada. Faça login novamente.');
      case 403:
        return ApiException(statusCode: statusCode, message: detail ?? 'Sem permissão para esta ação.');
      case 409:
        return ApiException(statusCode: statusCode, message: detail ?? 'Conflito: operação não permitida no estado atual.');
      case 422:
        return ApiException(statusCode: statusCode, message: detail ?? 'Dados inválidos. Verifique os campos.');
      case 500:
        return ApiException(statusCode: statusCode, message: detail ?? 'Erro interno do servidor. Tente novamente.');
      default:
        return ApiException(statusCode: statusCode, message: detail ?? 'Erro inesperado (HTTP $statusCode).');
    }
  }

  @override
  String toString() => 'ApiException($statusCode): $message';
}

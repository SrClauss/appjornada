import 'package:dio/dio.dart';
import '../auth/token_storage.dart';
import '../errors/api_exception.dart';

const String _apiBaseUrl =
    String.fromEnvironment('API_BASE_URL', defaultValue: 'http://10.0.2.2:8000');

Dio? _instance;

Dio get apiClient {
  _instance ??= _buildDio();
  return _instance!;
}

Dio _buildDio() {
  final dio = Dio(
    BaseOptions(
      baseUrl: _apiBaseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
      contentType: 'application/json',
    ),
  );

  // Request interceptor — inject JWT
  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await TokenStorage.readToken();
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        handler.next(options);
      },
      onError: (DioException e, handler) async {
        final statusCode = e.response?.statusCode;
        if (statusCode == null) {
          handler.reject(e);
          return;
        }

        // 401 — clear token (caller is responsible for navigation)
        if (statusCode == 401) {
          await TokenStorage.deleteToken();
        }

        final detail = e.response?.data is Map
            ? (e.response!.data as Map)['detail']?.toString()
            : null;

        handler.reject(
          DioException(
            requestOptions: e.requestOptions,
            error: ApiException.fromStatusCode(statusCode, detail),
            response: e.response,
            type: e.type,
          ),
        );
      },
    ),
  );

  return dio;
}

/// Resets the singleton (useful in tests or after logout).
void resetApiClient() => _instance = null;

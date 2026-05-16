import 'package:dio/dio.dart';
import '../../../core/api/api_client.dart';
import '../../../core/api/endpoints.dart';
import '../../../core/auth/token_storage.dart';
import '../../../shared/models/user_model.dart';

class AuthService {
  /// Login via OAuth2 form-urlencoded → stores JWT token.
  static Future<void> login(String email, String pin) async {
    final response = await apiClient.post(
      Endpoints.login,
      data: 'username=${Uri.encodeComponent(email)}&password=${Uri.encodeComponent(pin)}',
      options: Options(contentType: 'application/x-www-form-urlencoded'),
    );
    final token = response.data['access_token'] as String;
    await TokenStorage.saveToken(token);
  }

  /// Retrieve the currently logged-in user's profile.
  static Future<UserModel> getMe() async {
    final response = await apiClient.get(Endpoints.me);
    return UserModel.fromJson(response.data as Map<String, dynamic>);
  }

  /// Logout — removes the stored token.
  static Future<void> logout() async {
    await TokenStorage.deleteToken();
    resetApiClient();
  }
}

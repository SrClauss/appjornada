import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class TokenStorage {
  static const _storage = FlutterSecureStorage();
  static const _key = 'jwt_token';

  static Future<void> saveToken(String token) =>
      _storage.write(key: _key, value: token);

  static Future<String?> readToken() => _storage.read(key: _key);

  static Future<void> deleteToken() => _storage.delete(key: _key);
}

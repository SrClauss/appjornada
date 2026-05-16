import 'dart:io';
import 'package:dio/dio.dart';
import '../../core/api/api_client.dart';
import '../../core/api/endpoints.dart';

class UploadService {
  /// Uploads a file to POST /uploads/ and returns the public URL.
  static Future<String> uploadFoto(File file) async {
    final formData = FormData.fromMap({
      'file': await MultipartFile.fromFile(
        file.path,
        filename: file.path.split('/').last,
      ),
    });
    final response = await apiClient.post(
      Endpoints.uploads,
      data: formData,
      options: Options(contentType: 'multipart/form-data'),
    );
    // API returns {"url": "..."} or {"filename": "...", "url": "..."}
    final data = response.data as Map<String, dynamic>;
    return data['url'] as String? ?? data['filename'] as String;
  }
}

import 'dart:io';
import 'package:dio/dio.dart';
import '../../core/api/api_client.dart';
import '../../core/api/endpoints.dart';

class UploadService {
  /// Uploads a file to POST /uploads/{contexto} and returns the public URL.
  ///
  /// [contexto] must be one of: km_inicial, km_final, cnh, clrv, comprovante,
  /// sinistro, nota_fiscal, outros.
  static Future<String> uploadFoto(
    File file, {
    String contexto = 'outros',
  }) async {
    final formData = FormData.fromMap({
      'arquivo': await MultipartFile.fromFile(
        file.path,
        filename: file.path.split('/').last,
      ),
    });
    final response = await apiClient.post(
      '${Endpoints.uploads}/$contexto',
      data: formData,
      options: Options(contentType: 'multipart/form-data'),
    );
    final data = response.data as Map<String, dynamic>;
    return data['url'] as String;
  }
}

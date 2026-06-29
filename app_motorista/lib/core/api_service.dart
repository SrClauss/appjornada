import 'dart:convert';
import 'package:http/http.dart' as http;

const String defaultApiUrl = 'http://2.24.121.189:3000/api';

class ApiService {
  static String baseUrl = defaultApiUrl;
  static String? token;
  static String? motoristaId;
  static String? motoristaNome;

  static void init(String url, String? t, String? mId, String? mNome) {
    baseUrl = url;
    token = t;
    motoristaId = mId;
    motoristaNome = mNome;
  }

  static Map<String, String> get headers => {
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      };

  // Upload de arquivo para o MinIO / Servidor
  static Future<String?> uploadFile(String filePath, String contexto) async {
    try {
      final uri = Uri.parse('$baseUrl/uploads/$contexto');
      final request = http.MultipartRequest('POST', uri);
      
      if (token != null) {
        request.headers['Authorization'] = 'Bearer $token';
      }
      
      request.files.add(await http.MultipartFile.fromPath('arquivo', filePath));
      
      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);
      
      if (response.statusCode == 201) {
        final body = json.decode(response.body);
        return body['url'];
      } else {
        print('[ApiService] Erro no upload (${response.statusCode}): ${response.body}');
      }
    } catch (e) {
      print('[ApiService] Erro ao enviar arquivo: $e');
    }
    return null;
  }

  // Upload e processamento automático do print de faturamento usando Gemini no servidor
  static Future<Map<String, dynamic>?> uploadAndProcessComprovante(String filePath, {String? plataforma}) async {
    try {
      final uri = Uri.parse('$baseUrl/jornadas/aberta/comprovante');
      final request = http.MultipartRequest('POST', uri);
      
      if (token != null) {
        request.headers['Authorization'] = 'Bearer $token';
      }
      
      request.files.add(await http.MultipartFile.fromPath('arquivo', filePath));
      if (plataforma != null) {
        request.fields['plataforma'] = plataforma;
      }
      
      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);
      
      if (response.statusCode == 201) {
        return json.decode(response.body);
      } else {
        print('[ApiService] Erro no processamento (${response.statusCode}): ${response.body}');
      }
    } catch (e) {
      print('[ApiService] Erro ao enviar comprovante: $e');
    }
    return null;
  }
}

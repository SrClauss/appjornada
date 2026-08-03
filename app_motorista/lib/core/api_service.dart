import 'dart:convert';
import 'package:http/http.dart' as http;

const String defaultApiUrl = 'https://rafael.arkana.fun/api';

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

  // Upload e leitura por IA do Hodômetro via Gemini
  static Future<Map<String, dynamic>?> processarFotoOdometro(String filePath, {String contexto = 'km_inicial'}) async {
    try {
      final uri = Uri.parse('$baseUrl/ocr/odometro');
      final request = http.MultipartRequest('POST', uri);
      
      if (token != null) {
        request.headers['Authorization'] = 'Bearer $token';
      }
      
      request.files.add(await http.MultipartFile.fromPath('file', filePath));
      request.fields['contexto'] = contexto;
      
      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        print('[ApiService] Erro OCR Odômetro (${response.statusCode}): ${response.body}');
      }
    } catch (e) {
      print('[ApiService] Erro ao enviar foto do hodômetro: $e');
    }
    return null;
  }

  // Upload e processamento automático do print de faturamento usando Gemini no servidor
  // Upload e processamento automático do print de faturamento usando Gemini no servidor
  static Future<Map<String, dynamic>?> uploadAndProcessComprovante(
    String filePath, {
    String? plataforma,
    double? startLat,
    double? startLon,
    double? endLat,
    double? endLon,
    int? startTime,
    int? endTime,
    List<Map<String, double>>? routePoints,
  }) async {
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
      if (startLat != null) request.fields['start_lat'] = startLat.toString();
      if (startLon != null) request.fields['start_lon'] = startLon.toString();
      if (endLat != null) request.fields['end_lat'] = endLat.toString();
      if (endLon != null) request.fields['end_lon'] = endLon.toString();
      if (startTime != null) request.fields['start_time'] = startTime.toString();
      if (endTime != null) request.fields['end_time'] = endTime.toString();
      if (routePoints != null) {
        request.fields['route_points'] = json.encode(routePoints);
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

  // Salva correção manual de comprovante
  static Future<Map<String, dynamic>?> revisarComprovante({
    required String urlComprovante,
    required String plataforma,
    required double valor,
    String? origem,
    String? destino,
  }) async {
    try {
      final uri = Uri.parse('$baseUrl/jornadas/aberta/comprovante/revisao');
      final request = http.MultipartRequest('POST', uri);
      
      if (token != null) {
        request.headers['Authorization'] = 'Bearer $token';
      }
      
      request.fields['url_comprovante'] = urlComprovante;
      request.fields['plataforma'] = plataforma;
      request.fields['valor'] = valor.toString();
      if (origem != null) request.fields['origem'] = origem;
      if (destino != null) request.fields['destino'] = destino;
      
      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);
      
      if (response.statusCode == 201) {
        return json.decode(response.body);
      } else {
        print('[ApiService] Erro na revisão (${response.statusCode}): ${response.body}');
      }
    } catch (e) {
      print('[ApiService] Erro ao revisar comprovante: $e');
    }
    return null;
  }

  // Deleta um comprovante da jornada
  static Future<Map<String, dynamic>?> deletarComprovante(String urlComprovante) async {
    try {
      final uri = Uri.parse('$baseUrl/jornadas/aberta/comprovante/deletar');
      final request = http.MultipartRequest('POST', uri);
      
      if (token != null) {
        request.headers['Authorization'] = 'Bearer $token';
      }
      
      request.fields['url_comprovante'] = urlComprovante;
      
      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);
      
      if (response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        print('[ApiService] Erro ao deletar comprovante (${response.statusCode}): ${response.body}');
      }
    } catch (e) {
      print('[ApiService] Erro ao deletar comprovante: $e');
    }
    return null;
  }

  // Busca configurações de inatividade do backend
  static Future<Map<String, dynamic>?> getConfigInatividade() async {
    try {
      final res = await http.get(
        Uri.parse('$baseUrl/config/inatividade'),
        headers: headers,
      );
      if (res.statusCode == 200) {
        return json.decode(res.body);
      }
    } catch (e) {
      print('[ApiService] Erro ao buscar configs de inatividade: $e');
    }
    return null;
  }

  // Busca pendências de auditoria/KM morta do motorista logado
  static Future<List<dynamic>> getPendenciasMotorista() async {
    try {
      final res = await http.get(
        Uri.parse('$baseUrl/users/me/pendencias'),
        headers: headers,
      );
      if (res.statusCode == 200) {
        return json.decode(res.body) as List<dynamic>;
      }
    } catch (e) {
      print('[ApiService] Erro ao buscar pendências do motorista: $e');
    }
    return [];
  }

  // Resolve pendência de auditoria/KM morta
  static Future<bool> resolverPendenciaMotorista(String pendenciaId, Map<String, dynamic> dados) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/users/me/pendencias/$pendenciaId/resolver'),
        headers: headers,
        body: json.encode(dados),
      );
      return res.statusCode == 200;
    } catch (e) {
      print('[ApiService] Erro ao resolver pendência do motorista: $e');
    }
    return false;
  }

  // Upload e processamento do vídeo de gravação do extrato de corridas
  static Future<Map<String, dynamic>?> uploadExtratoVideo(String filePath) async {
    try {
      final uri = Uri.parse('$baseUrl/jornadas/aberta/extrato-video');
      final request = http.MultipartRequest('POST', uri);
      
      if (token != null) {
        request.headers['Authorization'] = 'Bearer $token';
      }
      
      request.files.add(await http.MultipartFile.fromPath('arquivo', filePath));
      
      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);
      
      if (response.statusCode == 201 || response.statusCode == 200) {
        return json.decode(response.body);
      } else {
        print('[ApiService] Erro ao enviar vídeo do extrato (${response.statusCode}): ${response.body}');
      }
    } catch (e) {
      print('[ApiService] Erro ao enviar vídeo do extrato: $e');
    }
    return null;
  }
}



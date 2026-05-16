import 'package:dio/dio.dart';
import '../../../core/api/api_client.dart';
import '../../../core/api/endpoints.dart';
import '../../../shared/models/jornada_model.dart';
import '../../../shared/models/veiculo_model.dart';

class JornadaService {
  /// Fetch list of available vehicles.
  static Future<List<VeiculoModel>> getVeiculos() async {
    final response = await apiClient.get(Endpoints.veiculos);
    final list = response.data as List<dynamic>;
    return list
        .map((e) => VeiculoModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Open a new jornada.
  /// [pin] is the driver's 4-digit PIN.
  /// [lat]/[lon] are optional GPS coordinates.
  static Future<JornadaModel> abrirJornada({
    required String motoristaId,
    required String veiculoId,
    required double kmInicial,
    String? kmInicialUrl,
    required String pin,
    double? lat,
    double? lon,
  }) async {
    final queryParams = <String, dynamic>{'pin': pin};
    if (lat != null) queryParams['localizacao_lat'] = lat;
    if (lon != null) queryParams['localizacao_lon'] = lon;

    final body = <String, dynamic>{
      'motorista_id': motoristaId,
      'veiculo_id': veiculoId,
      'km': {'inicial': kmInicial},
      if (kmInicialUrl != null) 'fotos': {'km_inicial_url': kmInicialUrl},
    };

    final response = await apiClient.post(
      Endpoints.jornadas,
      queryParameters: queryParams,
      data: body,
    );
    return JornadaModel.fromJson(response.data as Map<String, dynamic>);
  }

  /// Fetch the currently open jornada (null if none).
  static Future<JornadaModel?> getJornadaAberta() async {
    try {
      final response = await apiClient.get(Endpoints.jornadaAberta);
      final data = response.data;
      if (data == null) return null;
      return JornadaModel.fromJson(data as Map<String, dynamic>);
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) return null;
      rethrow;
    }
  }

  /// Pause the jornada.
  static Future<JornadaModel> pausarJornada({
    required String jornadaId,
    required String tipo,
    double? lat,
    double? lon,
  }) async {
    final queryParams = <String, dynamic>{'tipo': tipo};
    final body = <String, dynamic>{
      if (lat != null && lon != null)
        'localizacao_inicio': {'lat': lat, 'lon': lon},
    };

    final response = await apiClient.post(
      '${Endpoints.jornadas}/$jornadaId/pausas',
      queryParameters: queryParams,
      data: body.isEmpty ? null : body,
    );
    return JornadaModel.fromJson(response.data as Map<String, dynamic>);
  }

  /// Resume a paused jornada.
  static Future<JornadaModel> retomarJornada({
    required String jornadaId,
    required String pausaId,
    double? lat,
    double? lon,
  }) async {
    final body = <String, dynamic>{
      if (lat != null && lon != null)
        'localizacao_fim': {'lat': lat, 'lon': lon},
    };

    final response = await apiClient.patch(
      '${Endpoints.jornadas}/$jornadaId/pausas/$pausaId/fechar',
      data: body.isEmpty ? null : body,
    );
    return JornadaModel.fromJson(response.data as Map<String, dynamic>);
  }

  /// Close (finish) the jornada.
  static Future<JornadaModel> fecharJornada({
    required String jornadaId,
    required double kmFinal,
    double faturamentoUber = 0,
    double faturamento99 = 0,
    double faturamentoOutros = 0,
    String? fotoKmFinalUrl,
    double? lat,
    double? lon,
    String? observacoes,
  }) async {
    final queryParams = <String, dynamic>{
      'km_final': kmFinal,
      'faturamento_uber': faturamentoUber,
      'faturamento_99': faturamento99,
      'faturamento_outros': faturamentoOutros,
      if (fotoKmFinalUrl != null) 'foto_km_final_url': fotoKmFinalUrl,
      if (lat != null) 'localizacao_lat': lat,
      if (lon != null) 'localizacao_lon': lon,
      if (observacoes != null && observacoes.isNotEmpty)
        'observacoes': observacoes,
    };

    final response = await apiClient.patch(
      '${Endpoints.jornadas}/$jornadaId/fechar',
      queryParameters: queryParams,
    );
    return JornadaModel.fromJson(response.data as Map<String, dynamic>);
  }

  /// Register a refuelling (abastecimento).
  static Future<void> registrarAbastecimento({
    required String jornadaId,
    required double km,
    double valorGasolina = 0,
    double valorGnv = 0,
    double valorEtanol = 0,
    String? fotoComprovanteUrl,
  }) async {
    final body = <String, dynamic>{
      'km': km,
      'valor_gasolina': valorGasolina,
      'valor_gnv': valorGnv,
      'valor_etanol': valorEtanol,
      if (fotoComprovanteUrl != null) 'foto_comprovante_url': fotoComprovanteUrl,
    };
    await apiClient.post(
      '${Endpoints.jornadas}/$jornadaId/abastecimentos',
      data: body,
    );
  }
}

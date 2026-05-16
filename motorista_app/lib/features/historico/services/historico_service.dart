import '../../../core/api/api_client.dart';
import '../../../core/api/endpoints.dart';
import '../../../shared/models/jornada_model.dart';

class HistoricoService {
  /// Returns a paginated list of jornadas for the authenticated motorista.
  ///
  /// The API automatically filters by the logged-in driver when
  /// `role == MOTORISTA`.
  static Future<List<JornadaModel>> getJornadas({
    int skip = 0,
    int limit = 20,
  }) async {
    final response = await apiClient.get(
      Endpoints.jornadas,
      queryParameters: {'skip': skip, 'limit': limit},
    );
    final list = response.data as List<dynamic>;
    return list
        .map((e) => JornadaModel.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}

import '../../../core/api/api_client.dart';
import '../../../core/api/endpoints.dart';

class PerfilService {
  /// Updates the authenticated user's profile fields.
  ///
  /// Only the fields allowed for `role == MOTORISTA` are sent.
  static Future<void> updatePerfil(
    String userId, {
    String? nome,
    String? telefone,
    String? cpf,
  }) async {
    final body = <String, dynamic>{};

    if (nome != null && nome.isNotEmpty) body['nome'] = nome;

    if (telefone != null || cpf != null) {
      final perfil = <String, dynamic>{};
      if (telefone != null) perfil['telefone'] = telefone;
      if (cpf != null) perfil['cpf'] = cpf;
      body['perfil_motorista'] = perfil;
    }

    if (body.isEmpty) return;

    await apiClient.patch(
      '${Endpoints.users}/$userId',
      data: body,
    );
  }
}

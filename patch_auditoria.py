import re

file_path = "app_motorista/lib/steps/auditoria_anterior_step.dart"
with open(file_path, "r") as f:
    content = f.read()

# Remove the manager audit check.
old_manager_audit = """    // 2. Verifica se a jornada anterior está encerrada mas com auditoria pendente pelo gestor
    try {
      final res = await http.get(
        Uri.parse('${ApiService.baseUrl}/jornadas/pendente-auditoria'),
        headers: ApiService.headers,
      ).timeout(const Duration(seconds: 4));

      if (res.statusCode == 200) {
        final body = json.decode(res.body);
        if (body is Map && body.isNotEmpty) {
          setState(() {
            _hasPendencia = false;
            _isPendenteAuditoriaGestor = true;
            _jornadaPendenteGestor = Map<String, dynamic>.from(body);
            _loading = false;
          });
          return;
        }
      }
    } catch (e) {
      print('[AuditoriaAnteriorStep] Erro ao checar auditoria pendente do gestor: $e');
    }

    setState(() {
      _hasPendencia = false;
      _pendenciaAtual = null;
      _isPendenteAuditoriaGestor = false;
      _loading = false;
    });"""

new_manager_audit = """    // Auditoria do gestor removida! O motorista não é mais bloqueado.
    
    // Como não há pendências do motorista, pula direto para a próxima etapa (Veículo).
    widget.onCompleted();"""

content = content.replace(old_manager_audit, new_manager_audit)

with open(file_path, "w") as f:
    f.write(content)
print("Patched AuditoriaAnteriorStep")

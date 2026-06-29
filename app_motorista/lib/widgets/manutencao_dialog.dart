import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:app_motorista/core/api_service.dart';

class ManutencaoDialog extends StatelessWidget {
  final Map<String, dynamic> jornada;
  final Function(String, Map<String, dynamic>?) onCompleted;
  const ManutencaoDialog({super.key, required this.jornada, required this.onCompleted});

  Future<void> _entrarManutencaoRapida(BuildContext context) async {
    try {
      final jId = jornada['_id'] ?? jornada['id'];
      final res = await http.post(
        Uri.parse('${ApiService.baseUrl}/jornadas/$jId/pausas?tipo=MANUTENCAO&localizacao_lat=-20.219&localizacao_lon=-40.264'),
        headers: ApiService.headers,
      );
      if (res.statusCode == 201) {
        final body = json.decode(res.body);
        onCompleted('pause', body);
      }
    } catch (_) {}
  }

  Future<void> _entrarManutencaoDemorada(BuildContext context) async {
    try {
      final jId = jornada['_id'] ?? jornada['id'];
      // Deixar na oficina encerra a jornada imediatamente
      final res = await http.patch(
        Uri.parse('${ApiService.baseUrl}/jornadas/$jId/fechar?km_final=50000.0&observacoes=Deixado+na+oficina'),
        headers: ApiService.headers,
      );
      if (res.statusCode == 200) {
        onCompleted('close', null);
      }
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Registrar Entrada em Oficina'),
      content: const Text(
        'Escolha o tipo de manutenção para continuarmos:',
      ),
      actionsPadding: const EdgeInsets.all(16),
      actions: [
        Column(
          children: [
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF6366F1),
                minimumSize: const Size.fromHeight(48),
              ),
              onPressed: () => _entrarManutencaoRapida(context),
              child: const Text('Opção A: Aguardar na Oficina (Pausa Shift)', style: TextStyle(color: Colors.white)),
            ),
            const SizedBox(height: 12),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.redAccent,
                minimumSize: const Size.fromHeight(48),
              ),
              onPressed: () => _entrarManutencaoDemorada(context),
              child: const Text('Opção B: Deixar Veículo (Encerrar Dia)', style: TextStyle(color: Colors.white)),
            ),
            const SizedBox(height: 12),
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancelar'),
            ),
          ],
        )
      ],
    );
  }
}

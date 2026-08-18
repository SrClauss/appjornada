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
      // Em vez de encerrar a jornada, entramos em MANUTENCAO_LONGA
      final res = await http.post(
        Uri.parse('${ApiService.baseUrl}/jornadas/$jId/pausas?tipo=MANUTENCAO_LONGA&localizacao_lat=-20.219&localizacao_lon=-40.264'),
        headers: ApiService.headers,
      );
      if (res.statusCode == 201) {
        final body = json.decode(res.body);
        onCompleted('pause', body); // Continua no app na tela de manutenção, mas o motorista pode deslogar.
      }
    } catch (_) {}
  }

  void _confirmarOpcaoA(BuildContext context) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1E293B),
        title: const Text('Confirmar Pausa Manutenção', style: TextStyle(color: Colors.white)),
        content: const Text('Deseja iniciar uma pausa para manutenção rápida? A jornada continuará aberta.', style: TextStyle(color: Colors.white70)),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('CANCELAR')),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(ctx);
              _entrarManutencaoRapida(context);
            },
            child: const Text('CONFIRMAR'),
          ),
        ],
      ),
    );
  }

  void _confirmarOpcaoB(BuildContext context) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1E293B),
        title: const Text('Deixar Veículo', style: TextStyle(color: Colors.white)),
        content: const Text('O veículo ficará na oficina. A sua jornada CONTINUARÁ RENTABILIZANDO HORAS até o limite da sua carga horária. Você poderá fechar o app e ir para casa. Deseja prosseguir?', style: TextStyle(color: Colors.white70)),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('CANCELAR')),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Colors.amber[800], foregroundColor: Colors.white),
            onPressed: () {
              Navigator.pop(ctx);
              _entrarManutencaoDemorada(context);
            },
            child: const Text('CONFIRMAR SAÍDA'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: const Color(0xFF0F172A),
      title: const Text('Registrar Entrada em Oficina', style: TextStyle(color: Colors.white)),
      content: const Text(
        'Escolha o tipo de manutenção para continuarmos:',
        style: TextStyle(color: Colors.white70),
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
              onPressed: () => _confirmarOpcaoA(context),
              child: const Text('Opção A: Aguardar na Oficina (Pausa Shift)', style: TextStyle(color: Colors.white)),
            ),
            const SizedBox(height: 12),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.amber[800],
                minimumSize: const Size.fromHeight(48),
              ),
              onPressed: () => _confirmarOpcaoB(context),
              child: const Text('Opção B: Deixar Veículo (Pausa Remunerada)', style: TextStyle(color: Colors.white)),
            ),
            const SizedBox(height: 12),
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancelar', style: TextStyle(color: Colors.grey)),
            ),
          ],
        )
      ],
    );
  }
}

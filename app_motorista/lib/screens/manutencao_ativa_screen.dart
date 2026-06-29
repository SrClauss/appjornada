import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:app_motorista/core/api_service.dart';

class ManutencaoAtivaScreen extends StatefulWidget {
  final Map<String, dynamic> jornada;
  final Function(Map<String, dynamic>) onResume;
  final VoidCallback onLogout;
  const ManutencaoAtivaScreen({super.key, required this.jornada, required this.onResume, required this.onLogout});

  @override
  State<ManutencaoAtivaScreen> createState() => _ManutencaoAtivaScreenState();
}

class _ManutencaoAtivaScreenState extends State<ManutencaoAtivaScreen> {
  bool _loading = false;

  Future<void> _concluirManutencao() async {
    setState(() {
      _loading = true;
    });

    try {
      // Acha a pausa ativa do tipo MANUTENCAO
      final pausas = widget.jornada['pausas'] as List;
      final manutencaoPausa = pausas.firstWhere(
        (p) => p['tipo'] == 'MANUTENCAO' && p['fim'] == null,
        orElse: () => null,
      );

      if (manutencaoPausa != null) {
        final jId = widget.jornada['_id'] ?? widget.jornada['id'];
        final res = await http.patch(
          Uri.parse('${ApiService.baseUrl}/jornadas/$jId/pausas/${manutencaoPausa['id']}/fechar'),
          headers: ApiService.headers,
        );

        if (res.statusCode == 200) {
          final body = json.decode(res.body);
          widget.onResume(body);
        }
      }
    } catch (_) {} finally {
      setState(() {
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Manutenção Ativa'),
        automaticallyImplyLeading: false,
        backgroundColor: const Color(0xFF1E293B),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: widget.onLogout,
            tooltip: 'Sair / Deslogar',
          ),
        ],
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              const Icon(Icons.build, size: 80, color: Colors.redAccent),
              const SizedBox(height: 24),
              const Text(
                'Veículo em Manutenção',
                style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Colors.white),
              ),
              const SizedBox(height: 12),
              const Text(
                'Sua jornada de trabalho está pausada temporariamente enquanto o carro está na oficina. Aguarde a conclusão.',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey),
              ),
              const SizedBox(height: 48),
              SizedBox(
                width: double.infinity,
                height: 56,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF10B981)),
                  onPressed: _loading ? null : _concluirManutencao,
                  child: _loading
                      ? const CircularProgressIndicator(color: Colors.white)
                      : const Text('REINICIAR JORNADA (SAIR DA OFICINA)', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.white)),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:app_motorista/core/api_service.dart';

class VeiculoStep extends StatefulWidget {
  final Function(Map<String, dynamic>) onVeiculoSelected;
  const VeiculoStep({super.key, required this.onVeiculoSelected});

  @override
  State<VeiculoStep> createState() => _VeiculoStepState();
}

class _VeiculoStepState extends State<VeiculoStep> {
  bool _loading = true;
  List<dynamic> _veiculos = [];

  @override
  void initState() {
    super.initState();
    _fetchVeiculos();
  }

  Future<void> _fetchVeiculos() async {
    try {
      final res = await http.get(
        Uri.parse('${ApiService.baseUrl}/veiculos'),
        headers: ApiService.headers,
      );
      if (res.statusCode == 200) {
        setState(() {
          _veiculos = json.decode(res.body);
          _loading = false;
        });
      } else {
        // Mock se falhar
        _setMockVeiculos();
      }
    } catch (_) {
      _setMockVeiculos();
    }
  }

  void _setMockVeiculos() {
    setState(() {
      _veiculos = [
        {'id_placa': 'TST1A23', 'marca_modelo': 'FIAT/UNO ATTRACTIVE 1.0', 'cor': 'BRANCO', 'situacao': 'RODANDO', 'km_atual': 50000.0},
        {'id_placa': 'ABC1D23', 'marca_modelo': 'VW/GOL', 'cor': 'PRATA', 'situacao': 'RODANDO', 'km_atual': 82300.0},
        {'id_placa': 'XYZ9K88', 'marca_modelo': 'HYU/HB20', 'cor': 'AZUL', 'situacao': 'RODANDO', 'km_atual': 12400.0},
      ];
      _loading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    return Padding(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Selecione o veículo que irá dirigir hoje',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
          ),
          const SizedBox(height: 16),
          Expanded(
            child: ListView.builder(
              itemCount: _veiculos.length,
              itemBuilder: (context, idx) {
                final v = _veiculos[idx];
                return Card(
                  margin: const EdgeInsets.only(bottom: 16),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  child: ListTile(
                    contentPadding: const EdgeInsets.all(16),
                    leading: Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: const Color(0xFF6366F1).withOpacity(0.1),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(Icons.directions_car, color: Color(0xFF818CF8)),
                    ),
                    title: Text(
                      v['id_placa'],
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
                    ),
                    subtitle: Text('${v['marca_modelo']} • ${v['cor']}'),
                    trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                    onTap: () => widget.onVeiculoSelected(v),
                  ),
                );
              },
            ),
          )
        ],
      ),
    );
  }
}

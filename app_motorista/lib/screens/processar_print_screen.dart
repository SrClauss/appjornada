import 'dart:io';
import 'package:flutter/material.dart';
import 'package:app_motorista/core/api_service.dart';

class ProcessarPrintScreen extends StatefulWidget {
  final String imagePath;
  final VoidCallback onCompleted;

  const ProcessarPrintScreen({
    super.key,
    required this.imagePath,
    required this.onCompleted,
  });

  @override
  State<ProcessarPrintScreen> createState() => _ProcessarPrintScreenState();
}

class _ProcessarPrintScreenState extends State<ProcessarPrintScreen> {
  bool _loading = false;
  String? _selectedPlatform;

  Future<void> _processImage(String platform) async {
    setState(() {
      _loading = true;
      _selectedPlatform = platform;
    });

    try {
      final res = await ApiService.uploadAndProcessComprovante(
        widget.imagePath,
        plataforma: platform,
      );

      if (res != null && res['status'] == 'sucesso') {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Recibo processado! R\$ ${res['valor_extraido'].toStringAsFixed(2)} adicionados ao faturamento.',
            ),
            backgroundColor: Colors.green,
          ),
        );
        widget.onCompleted();
      } else {
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Não foi possível ler as informações do print. O comprovante foi anexado.'),
            backgroundColor: Colors.orange,
          ),
        );
        widget.onCompleted();
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Erro de rede: $e'),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        title: const Text('Classificar Print'),
        backgroundColor: const Color(0xFF1E293B),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: widget.onCompleted,
        ),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'Classifique este print para a IA processar:',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),
              Expanded(
                child: Container(
                  decoration: BoxDecoration(
                    color: const Color(0xFF1E293B),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: Colors.white10),
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(16),
                    child: Image.file(
                      File(widget.imagePath),
                      fit: BoxFit.contain,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 24),
              if (_loading)
                Column(
                  children: [
                    const CircularProgressIndicator(),
                    const SizedBox(height: 16),
                    Text(
                      'Enviando e processando print via IA ($_selectedPlatform)...',
                      style: const TextStyle(color: Colors.white70),
                    ),
                  ],
                )
              else
                Row(
                  children: [
                    Expanded(
                      child: SizedBox(
                        height: 56,
                        child: ElevatedButton(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.black, // Cor preta para o Uber
                            foregroundColor: Colors.white,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(16),
                              side: const BorderSide(color: Colors.white24),
                            ),
                          ),
                          onPressed: () => _processImage('UBER'),
                          child: const Text(
                            'UBER',
                            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: SizedBox(
                        height: 56,
                        child: ElevatedButton(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0xFFFFCC00), // Cor amarela para o 99
                            foregroundColor: Colors.black,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(16),
                            ),
                          ),
                          onPressed: () => _processImage('99'),
                          child: const Text(
                            '99 TAXI',
                            style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              const SizedBox(height: 16),
              if (!_loading)
                OutlinedButton(
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.grey,
                    side: const BorderSide(color: Colors.white24),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                    padding: const EdgeInsets.symmetric(vertical: 16),
                  ),
                  onPressed: () => _processImage('OUTROS'),
                  child: const Text('OUTRA PLATAFORMA / INDEPENDENTE'),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

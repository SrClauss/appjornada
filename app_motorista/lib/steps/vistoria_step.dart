import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:app_motorista/core/api_service.dart';

class VistoriaStep extends StatefulWidget {
  final Map<String, bool> checklist;
  final String observacoes;
  final String? fotoAvariaUrl;
  final Function(Map<String, bool>, String, String?) onCompleted;
  const VistoriaStep({
    super.key,
    required this.checklist,
    required this.observacoes,
    this.fotoAvariaUrl,
    required this.onCompleted,
  });

  @override
  State<VistoriaStep> createState() => _VistoriaStepState();
}

class _VistoriaStepState extends State<VistoriaStep> {
  late Map<String, bool> _localChecklist;
  final _obsController = TextEditingController();
  String? _fotoAvariaUrl;
  bool _loading = false;
  final ImagePicker _picker = ImagePicker();

  @override
  void initState() {
    super.initState();
    _localChecklist = Map.from(widget.checklist);
    _obsController.text = widget.observacoes;
    _fotoAvariaUrl = widget.fotoAvariaUrl;
  }

  @override
  void dispose() {
    _obsController.dispose();
    super.dispose();
  }

  Future<void> _takeFoto() async {
    try {
      final XFile? photo = await _picker.pickImage(
        source: ImageSource.camera,
        maxWidth: 1024,
        maxHeight: 1024,
        imageQuality: 80,
      );
      if (photo != null) {
        setState(() {
          _loading = true;
        });
        
        final url = await ApiService.uploadFile(photo.path, 'vistoria');
        
        setState(() {
          _loading = false;
          if (url != null) {
            _fotoAvariaUrl = url;
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Foto de avarias anexada com sucesso!')),
            );
          } else {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Falha ao enviar a foto para o servidor.')),
            );
          }
        });
      }
    } catch (e) {
      setState(() {
        _loading = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erro ao capturar foto: $e')),
      );
    }
  }

  void _submitVistoria() {
    widget.onCompleted(_localChecklist, _obsController.text, _fotoAvariaUrl);
  }

  Widget _buildCheckItem(String key, String title, IconData icon) {
    final ok = _localChecklist[key] ?? true;
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      color: ok ? const Color(0xFF1E293B) : const Color(0xFF3F1D1D),
      child: ListTile(
        leading: Icon(icon, color: ok ? const Color(0xFF10B981) : const Color(0xFFEF4444)),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
        subtitle: Text(ok ? 'Conforme' : 'Irregular / Necessita Ajuste'),
        trailing: Switch(
          value: ok,
          activeColor: const Color(0xFF10B981),
          inactiveThumbColor: const Color(0xFFEF4444),
          onChanged: (val) {
            setState(() {
              _localChecklist[key] = val;
            });
          },
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Vistoria e Checklist Geral',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
          ),
          const SizedBox(height: 8),
          const Text('Verifique o veículo minuciosamente antes de iniciar a jornada.'),
          const SizedBox(height: 16),
          _buildCheckItem('pneus', 'Estado dos Pneus', Icons.adjust),
          _buildCheckItem('oleo', 'Nível do Óleo', Icons.opacity),
          _buildCheckItem('agua', 'Nível da Água', Icons.water_drop),
          _buildCheckItem('farois', 'Faróis e Lanternas', Icons.lightbulb_outline),
          _buildCheckItem('limpeza', 'Limpeza do Veículo', Icons.clean_hands_outlined),
          const SizedBox(height: 16),
          const Text('Observações / Avarias', style: TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          TextField(
            controller: _obsController,
            maxLines: 2,
            decoration: const InputDecoration(
              hintText: 'Registre amassados, riscos ou avarias encontradas...',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 16),
          OutlinedButton.icon(
            onPressed: _loading ? null : _takeFoto,
            icon: _loading
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2, color: Colors.indigoAccent),
                  )
                : Icon(
                    _fotoAvariaUrl == null ? Icons.camera_alt : Icons.check_circle,
                    color: _fotoAvariaUrl == null ? Colors.white : const Color(0xFF10B981),
                  ),
            label: Text(
              _fotoAvariaUrl == null ? 'Fotografar Avarias (Opcional)' : 'Foto Anexada (Alterar)',
              style: TextStyle(
                color: _fotoAvariaUrl == null ? Colors.white : const Color(0xFF10B981),
              ),
            ),
          ),
          const SizedBox(height: 24),
          SizedBox(
            width: double.infinity,
            height: 50,
            child: ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF6366F1)),
              onPressed: _submitVistoria,
              child: const Text('CONCLUIR VISTORIA', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
            ),
          )
        ],
      ),
    );
  }
}

import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:app_motorista/core/api_service.dart';
import 'package:app_motorista/core/fluent_theme.dart';

class LoginScreen extends StatefulWidget {
  final Function(String, String, String, String) onLoginSuccess;
  const LoginScreen({super.key, required this.onLoginSuccess});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _emailController = TextEditingController();
  List<Map<String, dynamic>> _motoristas = [];
  Map<String, dynamic>? _selectedMotorista;
  bool _loadingMotoristas = true;
  String _pin = '';

  @override
  void initState() {
    super.initState();
    _loadMotoristas();
  }

  Future<void> _loadMotoristas() async {
    try {
      final res = await http.get(Uri.parse('${ApiService.baseUrl}/auth/motoristas'));
      if (res.statusCode == 200) {
        final List<dynamic> data = json.decode(res.body);
        setState(() {
          _motoristas = data.map((e) => Map<String, dynamic>.from(e)).toList();
          _loadingMotoristas = false;
          if (_motoristas.isNotEmpty) {
            _selectedMotorista = _motoristas.first;
            _emailController.text = _selectedMotorista!['email'] ?? '';
          }
        });
      } else {
        setState(() {
          _loadingMotoristas = false;
        });
      }
    } catch (e) {
      setState(() {
        _loadingMotoristas = false;
      });
    }
  }
  bool _loading = false;
  String? _errorMessage;

  void _onKeyPress(String val) {
    if (_pin.length < 4) {
      setState(() {
        _pin += val;
        _errorMessage = null;
      });
    }
  }

  void _onBackspace() {
    if (_pin.isNotEmpty) {
      setState(() {
        _pin = _pin.substring(0, _pin.length - 1);
      });
    }
  }

  void _onClear() {
    setState(() {
      _pin = '';
    });
  }

  Future<void> _submitLogin() async {
    if (_pin.length < 4) {
      setState(() {
        _errorMessage = 'Preencha o PIN de 4 dígitos';
      });
      return;
    }
    setState(() {
      _loading = true;
      _errorMessage = null;
    });

    try {
      final res = await http.post(
        Uri.parse('${ApiService.baseUrl}/auth/login'),
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: {
          'username': _emailController.text,
          'password': _pin,
        },
      );

      if (res.statusCode == 200) {
        final data = json.decode(res.body);
        final token = data['access_token'];
        // Busca perfil
        final profileRes = await http.get(
          Uri.parse('${ApiService.baseUrl}/auth/me'),
          headers: {'Authorization': 'Bearer $token'},
        );
        if (profileRes.statusCode == 200) {
          final profile = json.decode(profileRes.body);
          final mId = profile['id'] ?? profile['_id'];
          widget.onLoginSuccess(token, mId.toString(), profile['nome'], _pin);
        }
      } else {
        setState(() {
          _errorMessage = 'E-mail ou PIN incorretos';
          _pin = '';
        });
      }
    } catch (e) {
      setState(() {
        _errorMessage = 'Erro ao conectar à API: $e';
      });
    } finally {
      setState(() {
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            colors: [FluentColors.background, Color(0xFF141B2D)],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
        ),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                const Spacer(),
                // LOGO / TÍTULO
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    ClipRRect(
                      borderRadius: BorderRadius.circular(16),
                      child: Image.asset(
                        'assets/images/app_logo.png',
                        width: 54,
                        height: 54,
                        fit: BoxFit.cover,
                      ),
                    ),
                    const SizedBox(width: 16),
                    const Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'JORNADA',
                          style: TextStyle(
                            fontSize: 24,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 2,
                            color: Colors.white,
                          ),
                        ),
                        Text(
                          'Gestão de Frota',
                          style: TextStyle(color: Color(0xFF818CF8), fontSize: 14),
                        ),
                      ],
                    )
                  ],
                ),
                const SizedBox(height: 32),
                const Text(
                  'Bem-vindo, Motorista',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Identifique-se para iniciar seu trilho diário',
                  style: TextStyle(color: Colors.grey),
                ),
                const SizedBox(height: 24),
                // FORM E-MAIL
                _loadingMotoristas
                    ? const Padding(
                        padding: EdgeInsets.symmetric(vertical: 12.0),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                            ),
                            SizedBox(width: 12),
                            Text('Carregando motoristas...', style: TextStyle(color: Colors.white70)),
                          ],
                        ),
                      )
                    : _motoristas.isEmpty
                        ? TextField(
                            controller: _emailController,
                            style: const TextStyle(color: Colors.white),
                            decoration: InputDecoration(
                              labelText: 'E-mail cadastrado',
                              labelStyle: const TextStyle(color: Colors.grey),
                              prefixIcon: const Icon(Icons.email_outlined, color: Colors.grey),
                              enabledBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(12),
                                borderSide: const BorderSide(color: Colors.grey),
                              ),
                              focusedBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(12),
                                borderSide: const BorderSide(color: Color(0xFF6366F1)),
                              ),
                            ),
                          )
                        : DropdownButtonFormField<Map<String, dynamic>>(
                            value: _selectedMotorista,
                            dropdownColor: const Color(0xFF1E1B4B),
                            style: const TextStyle(color: Colors.white, fontSize: 16),
                            isExpanded: true,
                            decoration: InputDecoration(
                              labelText: 'Selecione seu Nome',
                              labelStyle: const TextStyle(color: Colors.grey),
                              prefixIcon: const Icon(Icons.person_outline, color: Colors.grey),
                              enabledBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(12),
                                borderSide: const BorderSide(color: Colors.grey),
                              ),
                              focusedBorder: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(12),
                                borderSide: const BorderSide(color: Color(0xFF6366F1)),
                              ),
                            ),
                            items: _motoristas.map((m) {
                              return DropdownMenuItem<Map<String, dynamic>>(
                                value: m,
                                child: Text('${m['nome']} (${m['email']})'),
                              );
                            }).toList(),
                            onChanged: (val) {
                              setState(() {
                                _selectedMotorista = val;
                                _emailController.text = val?['email'] ?? '';
                              });
                            },
                          ),
                const SizedBox(height: 24),
                // INDICADORES DE PIN
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: List.generate(4, (index) {
                    final isFilled = index < _pin.length;
                    return Container(
                      margin: const EdgeInsets.symmetric(horizontal: 10),
                      width: 16,
                      height: 16,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: isFilled ? const Color(0xFF6366F1) : Colors.transparent,
                        border: Border.all(color: const Color(0xFF6366F1), width: 2),
                      ),
                    );
                  }),
                ),
                const SizedBox(height: 12),
                if (_errorMessage != null)
                  Text(
                     _errorMessage!,
                    style: const TextStyle(color: Colors.red, fontWeight: FontWeight.bold),
                  ),
                const Spacer(),
                // PIN PAD
                _buildPinPad(),
                const SizedBox(height: 16),
                SizedBox(
                  width: double.infinity,
                  height: 56,
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF6366F1),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                    ),
                    onPressed: _loading ? null : _submitLogin,
                    child: _loading
                        ? const CircularProgressIndicator(color: Colors.white)
                        : const Text('ENTRAR', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white)),
                  ),
                ),
                const SizedBox(height: 20),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildPinPad() {
    return Column(
      children: [
        for (var row in [
          ['1', '2', '3'],
          ['4', '5', '6'],
          ['7', '8', '9'],
        ])
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: row
                .map((key) => _buildPinPadButton(
                      text: key,
                      onPressed: () => _onKeyPress(key),
                    ))
                .toList(),
          ),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: [
            _buildPinPadButton(
              icon: Icons.clear,
              onPressed: _onClear,
            ),
            _buildPinPadButton(
              text: '0',
              onPressed: () => _onKeyPress('0'),
            ),
            _buildPinPadButton(
              icon: Icons.backspace_outlined,
              onPressed: _onBackspace,
            ),
          ],
        )
      ],
    );
  }

  Widget _buildPinPadButton({String? text, IconData? icon, required VoidCallback onPressed}) {
    return Container(
      margin: const EdgeInsets.all(8),
      width: 72,
      height: 72,
      child: OutlinedButton(
        style: OutlinedButton.styleFrom(
          shape: const CircleBorder(),
          side: const BorderSide(color: Color(0xFF334155), width: 1.5),
        ),
        onPressed: onPressed,
        child: text != null
            ? Text(
                text,
                style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: Colors.white),
              )
            : Icon(icon, size: 24, color: Colors.white),
      ),
    );
  }
}

import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:receive_sharing_intent/receive_sharing_intent.dart';

import 'package:app_motorista/core/api_service.dart';
import 'package:app_motorista/screens/login_screen.dart';
import 'package:app_motorista/screens/dashboard_screen.dart';
import 'package:app_motorista/screens/pausa_screen.dart';
import 'package:app_motorista/screens/manutencao_ativa_screen.dart';
import 'package:app_motorista/screens/processar_print_screen.dart';
import 'package:app_motorista/screens/corrida_particular_screen.dart';
import 'package:app_motorista/screens/fechamento_wizard_screen.dart';
import 'package:app_motorista/screens/revisao_comprovante_screen.dart';
import 'package:app_motorista/screens/comprovantes_history_screen.dart';
import 'package:app_motorista/core/overlay_service.dart';
import 'package:app_motorista/widgets/stepper_layout.dart';
import 'package:app_motorista/steps/auditoria_anterior_step.dart';
import 'package:app_motorista/steps/veiculo_step.dart';
import 'package:app_motorista/steps/vistoria_step.dart';
import 'package:app_motorista/steps/km_inicial_step.dart';
import 'package:app_motorista/steps/km_morta_step.dart';
import 'package:app_motorista/core/gps_service.dart';
import 'package:geolocator/geolocator.dart';

import 'package:app_motorista/core/fluent_theme.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await GpsService.initializeService();
  runApp(const AppJornadaMotorista());
}

class AppJornadaMotorista extends StatelessWidget {
  const AppJornadaMotorista({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Jornada Motorista',
      debugShowCheckedModeBanner: false,
      theme: FluentThemeData.theme,
      home: const MainRouter(),
    );
  }
}

// --- ROTEADOR PRINCIPAL ---
class MainRouter extends StatefulWidget {
  const MainRouter({super.key});

  @override
  State<MainRouter> createState() => _MainRouterState();
}

class _MainRouterState extends State<MainRouter> with WidgetsBindingObserver {
  String _currentScreen = 'splash'; // splash, login, trilho, dashboard, pausa, manutencao
  String _trilhoStep = 'auditoria'; // auditoria, veiculo, vistoria, km_inicial, km_morta
  bool _loading = false;
  
  // Dados coletados no fluxo
  Map<String, dynamic>? _selectedVeiculo;
  Map<String, dynamic>? _pendingRevisionData;
  Map<String, bool> _checklist = {
    'pneus': true,
    'oleo': true,
    'agua': true,
    'farois': true,
    'limpeza': true,
  };
  String _observacoesVistoria = '';
  double _kmInicial = 0;
  double _kmMortaValor = 0;
  String? _fotoHodometroInicialUrl;
  String? _fotoAvariaUrl;

  // Detalhes da jornada atual
  Map<String, dynamic>? _jornadaAberta;
  StreamSubscription? _intentSub;
  String? _sharedImagePath;
  String? _sharedDestinationQuery;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _checkSession();
    _initSharingIntentListener();
    _initOverlayListener();
  }

  void _initOverlayListener() {
    OverlayService.initialize();
    OverlayService.onRevisionRequest = (data) {
      setState(() {
        _pendingRevisionData = data;
        _currentScreen = 'revisao_comprovante';
      });
    };
    OverlayService.onPausaInatividadeRequest = () {
      _navigateToPausaInatividade();
    };
    OverlayService.getPendingRevision().then((data) {
      if (data != null && mounted) {
        setState(() {
          _pendingRevisionData = data;
          _currentScreen = 'revisao_comprovante';
        });
      }
    });
    OverlayService.getPendingPausaInatividade().then((pending) {
      if (pending == true && mounted) {
        _navigateToPausaInatividade();
      }
    });
  }

  Future<void> _navigateToPausaInatividade() async {
    try {
      final j = await _fetchJornadaAberta();
      if (j != null && mounted) {
        setState(() {
          _jornadaAberta = j;
          _currentScreen = 'pausa';
        });
      }
    } catch (e) {
      print("[MainRouter] Erro ao buscar jornada aberta para pausa por inatividade: $e");
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _intentSub?.cancel();
    super.dispose();
  }

  void _initSharingIntentListener() {
    _intentSub = ReceiveSharingIntent.instance.getMediaStream().listen((value) {
      if (value.isNotEmpty) {
        _handleSharedFiles(value);
      }
    }, onError: (err) {
      print("[SharingIntent] Erro no stream: $err");
    });

    ReceiveSharingIntent.instance.getInitialMedia().then((value) {
      if (value.isNotEmpty) {
        _handleSharedFiles(value);
      }
    });
  }

  Future<void> _handleSharedFiles(List<SharedMediaFile> files) async {
    final prefs = await SharedPreferences.getInstance();
    final savedToken = prefs.getString('token');
    final savedId = prefs.getString('motorista_id');
    if (savedToken == null || savedId == null || savedId == 'null') {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Faça login no aplicativo antes de compartilhar prints.')),
        );
      }
      return;
    }

    final savedUrl = prefs.getString('api_url') ?? defaultApiUrl;
    ApiService.init(savedUrl, savedToken, savedId, prefs.getString('motorista_nome'));

    final j = await _fetchJornadaAberta();
    if (j == null) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Nenhuma jornada ativa encontrada para associar os prints.')),
        );
      }
      return;
    }

    if (files.isNotEmpty) {
      final first = files.first;
      if (first.type == SharedMediaType.text || first.type == SharedMediaType.url || first.path.startsWith('http') || first.path.contains('maps') || first.path.contains('.gl') || first.path.contains('google.com')) {
        setState(() {
          _jornadaAberta = j;
          _sharedDestinationQuery = first.path;
          _currentScreen = 'corrida_particular';
        });
      } else {
        setState(() {
          _jornadaAberta = j;
          _sharedImagePath = first.path;
          _currentScreen = 'processar_print';
        });
      }
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      // Nao reseta a sessão se o motorista estiver no meio do wizard de abertura
      if (_currentScreen != 'trilho') {
        _checkSession();
      }
    }
  }

  Future<void> _checkSession() async {
    final prefs = await SharedPreferences.getInstance();
    final savedToken = prefs.getString('token');
    String savedUrl = prefs.getString('api_url') ?? defaultApiUrl;
    if (savedUrl.contains('rafael.arkana.fun') || savedUrl.contains('http://')) {
      savedUrl = defaultApiUrl;
      await prefs.setString('api_url', defaultApiUrl);
    }
    ApiService.baseUrl = savedUrl;
    final savedId = prefs.getString('motorista_id');
    final savedNome = prefs.getString('motorista_nome');

    if (savedToken != null && savedId != null && savedId != 'null') {
      ApiService.init(savedUrl, savedToken, savedId, savedNome);
      try {
        final results = await Future.wait([
          _fetchJornadaAberta(),
          _fetchJornadaPendenteFechamento(),
        ]);
        final j = results[0] ?? results[1];
        setState(() {
          _jornadaAberta = j;
          if (j != null) {
            final String status = j['status'] ?? 'ABERTA';
            if (status == 'EM_PAUSA') {
              _currentScreen = 'pausa';
            } else if (status == 'EM_MANUTENCAO') {
              _currentScreen = 'manutencao';
            } else if (status == 'PRE_FECHAMENTO') {
              GpsService.stopTracking();
              _currentScreen = 'fechamento_wizard';
            } else {
              if (_currentScreen == 'splash' || _currentScreen == 'login' || _currentScreen == 'trilho') {
                _currentScreen = 'dashboard';
              }
              GpsService.startTracking(j['_id'] ?? j['id']);
            }
          } else {
            // Se não há jornada aberta ou em pré-fechamento, envia o motorista para a verificação de auditoria anterior
            GpsService.stopTracking();
            OverlayService.stopOverlay();

            _currentScreen = 'trilho';
            _trilhoStep = 'auditoria';
          }
        });
        return;
      } catch (e) {
        // Token pode ter expirado ou inválido
        final prefs2 = await SharedPreferences.getInstance();
        await prefs2.remove('token');
        await prefs2.remove('motorista_id');
        await prefs2.remove('motorista_nome');
        await prefs2.remove('motorista_pin');
        ApiService.token = null;
        GpsService.stopTracking();
      }
    } else {
      GpsService.stopTracking();
    }
    setState(() {
      _currentScreen = 'login';
    });
  }

  Future<Map<String, dynamic>?> _fetchJornadaAberta() async {
    try {
      final res = await http
          .get(
            Uri.parse('${ApiService.baseUrl}/jornadas/aberta'),
            headers: ApiService.headers,
          )
          .timeout(const Duration(milliseconds: 2500));
      if (res.statusCode == 200) {
        final body = json.decode(res.body);
        return body is Map ? Map<String, dynamic>.from(body) : null;
      } else if (res.statusCode == 401) {
        throw Exception('UNAUTHENTICATED');
      }
    } catch (e) {
      // Ignora erro de timeout para acelerar inicialização
    }
    return null;
  }

  Future<Map<String, dynamic>?> _fetchJornadaPendenteFechamento() async {
    try {
      final res = await http
          .get(
            Uri.parse('${ApiService.baseUrl}/jornadas/pendente-fechamento'),
            headers: ApiService.headers,
          )
          .timeout(const Duration(milliseconds: 2500));
      if (res.statusCode == 200) {
        final body = json.decode(res.body);
        return body is Map ? Map<String, dynamic>.from(body) : null;
      }
    } catch (e) {
      print('[main] Erro ao buscar jornada pendente de fechamento: $e');
    }
    return null;
  }

  void _onLoginSuccess(String t, String id, String nome, String pin) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('token', t);
    await prefs.setString('motorista_id', id);
    await prefs.setString('motorista_nome', nome);
    await prefs.setString('motorista_pin', pin);
    ApiService.init(ApiService.baseUrl, t, id, nome);

    var j = await _fetchJornadaAberta();
    if (j == null) {
      j = await _fetchJornadaPendenteFechamento();
    }
    setState(() {
      _jornadaAberta = j;
      if (j != null) {
        final String status = j['status'] ?? 'ABERTA';
        if (status == 'EM_PAUSA') {
          _currentScreen = 'pausa';
        } else if (status == 'EM_MANUTENCAO') {
          _currentScreen = 'manutencao';
        } else if (status == 'PRE_FECHAMENTO') {
          GpsService.stopTracking();
          _currentScreen = 'fechamento_wizard';
        } else {
          _currentScreen = 'dashboard';
          GpsService.startTracking(j['_id'] ?? j['id']);
        }
      } else {
        _currentScreen = 'trilho';
        _trilhoStep = 'auditoria';
      }
    });
  }

  void _onLogout() async {
    if (_jornadaAberta != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Você possui uma jornada ativa. Encerre-a antes de sair.'),
          backgroundColor: Colors.redAccent,
        ),
      );
      return;
    }
    GpsService.stopTracking();
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('token');
    await prefs.remove('motorista_id');
    await prefs.remove('motorista_nome');
    await prefs.remove('motorista_pin');
    ApiService.token = null;
    setState(() {
      _currentScreen = 'login';
    });
  }

  @override
  Widget build(BuildContext context) {
    switch (_currentScreen) {
      case 'splash':
        return const Scaffold(
          body: Center(
            child: CircularProgressIndicator(),
          ),
        );
      case 'login':
        return LoginScreen(onLoginSuccess: _onLoginSuccess);
      case 'trilho':
        return _buildTrilhoWizard();
      case 'dashboard':
        return DashboardScreen(
          jornada: _jornadaAberta!,
          onAction: (action, data) async {
            if (action == 'pause') {
              GpsService.stopTracking();
              setState(() {
                _jornadaAberta = data;
                _currentScreen = 'pausa';
              });
            } else if (action == 'manutencao_rapida') {
              GpsService.stopTracking();
              setState(() {
                _jornadaAberta = data;
                _currentScreen = 'manutencao';
              });
            } else if (action == 'close') {
              GpsService.stopTracking();
              setState(() {
                _jornadaAberta = null;
                _currentScreen = 'trilho';
                _trilhoStep = 'auditoria';
              });
            } else if (action == 'corrida_particular') {
              setState(() {
                _currentScreen = 'corrida_particular';
              });
            } else if (action == 'close_wizard') {
              setState(() {
                _currentScreen = 'fechamento_wizard';
              });
            }
          },
          onLogout: _onLogout,
        );
      case 'pausa':
        return PausaScreen(
          jornada: _jornadaAberta!,
          onResume: (updatedJornada) {
            GpsService.startTracking(updatedJornada['_id'] ?? updatedJornada['id']);
            setState(() {
              _jornadaAberta = updatedJornada;
              _currentScreen = 'dashboard';
            });
          },
          onLogout: _onLogout,
        );
      case 'manutencao':
        return ManutencaoAtivaScreen(
          jornada: _jornadaAberta!,
          onResume: (updatedJornada) {
            GpsService.startTracking(updatedJornada['_id'] ?? updatedJornada['id']);
            setState(() {
              _jornadaAberta = updatedJornada;
              _currentScreen = 'dashboard';
            });
          },
          onLogout: _onLogout,
        );
      case 'processar_print':
        return ProcessarPrintScreen(
          imagePath: _sharedImagePath!,
          onCompleted: () {
            _checkSession();
          },
        );
      case 'corrida_particular':
        return CorridaParticularScreen(
          jornada: _jornadaAberta!,
          initialDestinationQuery: _sharedDestinationQuery,
          onJornadaUpdated: (updated) {
            setState(() {
              _jornadaAberta = updated;
            });
          },
          onBack: () {
            setState(() {
              _sharedDestinationQuery = null;
              _currentScreen = 'dashboard';
            });
          },
        );
      case 'fechamento_wizard':
        return FechamentoWizardScreen(
          jornada: _jornadaAberta!,
          onCompleted: () {
            setState(() {
              _jornadaAberta = null;
              _currentScreen = 'trilho';
              _trilhoStep = 'auditoria';
            });
          },
          onCancel: () {
            setState(() {
              _currentScreen = 'dashboard';
            });
          },
        );
      case 'revisao_comprovante':
        return RevisaoComprovanteScreen(
          revisionData: _pendingRevisionData!,
          onCompleted: () {
            setState(() {
              _pendingRevisionData = null;
              _currentScreen = 'dashboard';
            });
            _checkSession();
          },
        );

      default:
        return const Scaffold(body: Center(child: Text('Erro de Navegação')));
    }
  }

  Widget _buildTrilhoWizard() {
    return StepperLayout(
      currentStep: _trilhoStep,
      onLogout: _onLogout,
      onBack: _onTrilhoBack,
      child: _buildTrilhoStepContent(),
    );
  }

  void _onTrilhoBack() {
    setState(() {
      if (_trilhoStep == 'veiculo') {
        _trilhoStep = 'auditoria';
      } else if (_trilhoStep == 'vistoria') {
        _trilhoStep = 'veiculo';
      } else if (_trilhoStep == 'km_inicial') {
        _trilhoStep = 'vistoria';
      } else if (_trilhoStep == 'km_morta') {
        _trilhoStep = 'km_inicial';
      }
    });
  }

  Widget _buildTrilhoStepContent() {
    switch (_trilhoStep) {
      case 'auditoria':
        return AuditoriaAnteriorStep(
          onCompleted: () {
            setState(() {
              _trilhoStep = 'veiculo';
            });
          },
        );
      case 'veiculo':
        return VeiculoStep(
          onVeiculoSelected: (veiculo) {
            setState(() {
              _selectedVeiculo = veiculo;
              _trilhoStep = 'vistoria';
            });
          },
        );
      case 'vistoria':
        return VistoriaStep(
          checklist: _checklist,
          observacoes: _observacoesVistoria,
          fotoAvariaUrl: _fotoAvariaUrl,
          onCompleted: (checklist, obs, fotoAvaria) {
            setState(() {
              _checklist = checklist;
              _observacoesVistoria = obs;
              _fotoAvariaUrl = fotoAvaria;
              _trilhoStep = 'km_inicial';
            });
          },
        );
      case 'km_inicial':
        return KmInicialStep(
          veiculo: _selectedVeiculo!,
          initialKm: _kmInicial > 0 ? _kmInicial : null,
          fotoHodometroUrl: _fotoHodometroInicialUrl,
          onCompleted: (km, alertMorta, valorMorta, fotoUrl) {
            setState(() {
              _kmInicial = km;
              _kmMortaValor = valorMorta;
              _fotoHodometroInicialUrl = fotoUrl;
              if (alertMorta) {
                _trilhoStep = 'km_morta';
              } else {
                _iniciarJornada();
              }
            });
          },
        );
      case 'km_morta':
        return KmMortaStep(
          kmMorta: _kmMortaValor,
          onCompleted: () {
            _iniciarJornada();
          },
        );
      default:
        return const SizedBox();
    }
  }

  Future<void> _iniciarJornada() async {
    if (_loading) return;
    setState(() {
      _loading = true;
    });
    // Inicia a jornada via API
    try {
      final prefs = await SharedPreferences.getInstance();
      final pin = prefs.getString('motorista_pin') ?? '1234';
      
      double lat = -20.219;
      double lon = -40.264;
      try {
        final pos = await Geolocator.getCurrentPosition(
          desiredAccuracy: LocationAccuracy.high,
          timeLimit: const Duration(seconds: 4),
        );
        lat = pos.latitude;
        lon = pos.longitude;
      } catch (_) {}

      final res = await http.post(
        Uri.parse('${ApiService.baseUrl}/jornadas?pin=$pin&localizacao_lat=$lat&localizacao_lon=$lon'),
        headers: ApiService.headers,
        body: json.encode({
          'veiculo_id': _selectedVeiculo!['id_placa'],
          'km': {
            'inicial': _kmInicial,
            'morta': _kmMortaValor,
          },
          'vistoria': {
            'pneus_ok': _checklist['pneus'],
            'oleo_ok': _checklist['oleo'],
            'agua_ok': _checklist['agua'],
            'farois_ok': _checklist['farois'],
            'limpeza_ok': _checklist['limpeza'],
            'observacoes': _observacoesVistoria,
            'foto_avarias_url': _fotoAvariaUrl,
          },
          'fotos': {
            'km_inicial_url': _fotoHodometroInicialUrl,
          },
        }),
      );

      if (res.statusCode == 201) {
        final body = json.decode(res.body);
        final Map<String, dynamic> jornadaObj = body is Map ? Map<String, dynamic>.from(body) : {};
        setState(() {
          _jornadaAberta = jornadaObj;
          _currentScreen = 'dashboard';
        });
        GpsService.startTracking(jornadaObj['_id'] ?? jornadaObj['id']);
      } else {
        if (!mounted) return;
        String errorMsg = res.body;
        try {
          final errJson = json.decode(res.body);
          if (errJson is Map && errJson.containsKey('detail')) {
            errorMsg = errJson['detail'].toString();
          }
        } catch (_) {}

        showDialog(
          context: context,
          builder: (ctx) => AlertDialog(
            backgroundColor: const Color(0xFF1E293B),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            title: const Row(
              children: [
                Icon(Icons.warning_amber_rounded, color: Colors.amber, size: 28),
                SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'Não é possível iniciar',
                    style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                ),
              ],
            ),
            content: Text(
              errorMsg,
              style: const TextStyle(color: Colors.white70, fontSize: 14, height: 1.4),
            ),
            actions: [
              ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF6366F1),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
                onPressed: () => Navigator.pop(ctx),
                child: const Text('ENTENDIDO', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
        );
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erro de conexão com a API: $e')),
      );
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
        });
      }
    }
  }
}

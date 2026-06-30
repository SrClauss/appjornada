import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:geolocator/geolocator.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:app_motorista/core/api_service.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

class CorridaParticularScreen extends StatefulWidget {
  final Map<String, dynamic> jornada;
  final Function(Map<String, dynamic>) onJornadaUpdated;
  final VoidCallback onBack;
  final String? initialDestinationQuery;

  const CorridaParticularScreen({
    super.key,
    required this.jornada,
    required this.onJornadaUpdated,
    required this.onBack,
    this.initialDestinationQuery,
  });

  @override
  State<CorridaParticularScreen> createState() => _CorridaParticularScreenState();
}

class _CorridaParticularScreenState extends State<CorridaParticularScreen> {
  bool _loading = false;
  Map<String, dynamic>? _activeCorrida;
  final _kmController = TextEditingController();
  
  // Roteamento, busca de destino e estimativas
  final _destController = TextEditingController();
  List<dynamic> _suggestions = [];
  bool _searchingDest = false;
  Map<String, dynamic>? _selectedDest;
  double? _estimatedDistanceKm;
  double? _estimatedDurationMin;
  double? _estimatedPrice;
  bool _calculatingRoute = false;
  List<dynamic> _precosBands = [];
  List<LatLng> _routePoints = [];
  LatLng? _originLatLng;
  LatLng? _destLatLng;
  final MapController _mapController = MapController();

  // Timer para corrida ativa
  Timer? _timer;
  Duration _elapsed = Duration.zero;
  Timer? _pollingTimer;

  @override
  void initState() {
    super.initState();
    _checkActiveCorrida();
    _loadPrecosBands();
    _startPolling();
    if (widget.initialDestinationQuery != null && widget.initialDestinationQuery!.isNotEmpty) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _resolveAndSearchDestination(widget.initialDestinationQuery!);
      });
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    _pollingTimer?.cancel();
    _kmController.dispose();
    _destController.dispose();
    super.dispose();
  }

  void _checkActiveCorrida() {
    final list = widget.jornada['corridas_particulares'] as List?;
    if (list != null && list.isNotEmpty) {
      final active = list.firstWhere(
        (c) => c['status'] == 'EM_ANDAMENTO',
        orElse: () => null,
      );
      if (active != null) {
        setState(() {
          _activeCorrida = Map<String, dynamic>.from(active);
          final coords = _activeCorrida!['destino_coordenadas'] as List?;
          if (coords != null && coords.length >= 2) {
            _selectedDest = {
              'display_name': _activeCorrida!['destino_endereco'] ?? '',
              'lat': coords[1],
              'lon': coords[0],
            };
            _destController.text = _activeCorrida!['destino_endereco'] ?? '';
          }
        });
        _startTimer();
      }
    }
  }

  void _startTimer() {
    if (_activeCorrida == null) return;
    final startStr = _activeCorrida!['horario_inicio'];
    if (startStr != null) {
      final startDt = DateTime.parse(startStr).toLocal();
      _timer?.cancel();
      _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
        if (!mounted) return;
        setState(() {
          _elapsed = DateTime.now().difference(startDt);
        });
      });
    }
  }

  Future<void> _loadPrecosBands() async {
    try {
      final res = await http.get(
        Uri.parse('${ApiService.baseUrl}/config/precos-particulares'),
        headers: ApiService.headers,
      );
      if (res.statusCode == 200) {
        setState(() {
          _precosBands = json.decode(res.body);
        });
      }
    } catch (e) {
      print('Erro ao carregar faixas de preço: $e');
    }
  }

  void _startPolling() {
    _pollingTimer = Timer.periodic(const Duration(seconds: 4), (timer) {
      if (mounted) {
        _refreshJornada();
      }
    });
  }

  Future<void> _refreshJornada() async {
    try {
      final jId = widget.jornada['_id'] ?? widget.jornada['id'];
      final res = await http.get(
        Uri.parse('${ApiService.baseUrl}/jornadas/$jId'),
        headers: ApiService.headers,
      );
      if (res.statusCode == 200) {
        final updated = json.decode(res.body);
        widget.onJornadaUpdated(updated);
        _checkActiveCorrida();
        
        // Verifica se há temp_destino gravado pelo mapa
        final temp = updated['temp_destino'];
        if (temp != null) {
          final double lat = (temp['lat'] as num).toDouble();
          final double lon = (temp['lon'] as num).toDouble();
          final String endereco = temp['endereco'] ?? '';
          
          if (_selectedDest == null || 
              _selectedDest!['lat'] != lat || 
              _selectedDest!['lon'] != lon) {
            setState(() {
              _selectedDest = {
                'display_name': endereco,
                'lat': lat,
                'lon': lon,
              };
              _destController.text = endereco;
            });
            await _calculateRoute();
          }
        }
      }
    } catch (e) {
      print('Erro ao sincronizar jornada: $e');
    }
  }

  Future<void> _resolveAndSearchDestination(String query) async {
    if (query.trim().isEmpty) return;

    setState(() {
      _searchingDest = true;
      _suggestions.clear();
      _selectedDest = null;
      _estimatedDistanceKm = null;
      _estimatedDurationMin = null;
      _estimatedPrice = null;
    });

    if (query.contains('http') || query.contains('maps') || query.contains('.gl') || query.contains('google.com')) {
      try {
        final uri = Uri.parse('${ApiService.baseUrl}/gps/resolver-maps').replace(
          queryParameters: {'url': query}
        );
        final res = await http.get(uri, headers: ApiService.headers);
        if (res.statusCode == 200) {
          final resolved = json.decode(res.body);
          setState(() {
            _selectedDest = resolved;
            _destController.text = resolved['display_name'] ?? '';
            _suggestions.clear();
          });
          await _calculateRoute();

          // Sincroniza com backend temp_destino
          final jId = widget.jornada['_id'] ?? widget.jornada['id'];
          await http.post(
            Uri.parse('${ApiService.baseUrl}/gps/atualizar-destino').replace(
              queryParameters: {
                'jornada_id': jId,
                'lat': resolved['lat'].toString(),
                'lon': resolved['lon'].toString(),
                'endereco': resolved['display_name'] ?? '',
              }
            ),
            headers: ApiService.headers,
          );
          return;
        }
      } catch (e) {
        print('Erro ao resolver link do Maps: $e');
      }
    }
    
    await _searchDestination(query);
  }

  double? _calculatePrice(double distanceKm, double durationMin) {
    if (_precosBands.isEmpty) return null;
    
    final agora = DateTime.now();
    final horaMinutosStr = '${agora.hour.toString().padLeft(2, '0')}:${agora.minute.toString().padLeft(2, '0')}';
    
    for (var faixa in _precosBands) {
      final inicio = faixa['hora_inicio'] as String;
      final fim = faixa['hora_fim'] as String;
      
      bool matches = false;
      if (inicio.compareTo(fim) <= 0) {
        matches = horaMinutosStr.compareTo(inicio) >= 0 && horaMinutosStr.compareTo(fim) <= 0;
      } else {
        matches = horaMinutosStr.compareTo(inicio) >= 0 || horaMinutosStr.compareTo(fim) <= 0;
      }
      
      if (matches) {
        final precoKm = (faixa['preco_km'] as num).toDouble();
        final precoMin = (faixa['preco_minuto'] as num).toDouble();
        return (distanceKm * precoKm) + (durationMin * precoMin);
      }
    }
    
    final first = _precosBands.first;
    final precoKm = (first['preco_km'] as num).toDouble();
    final precoMin = (first['preco_minuto'] as num).toDouble();
    return (distanceKm * precoKm) + (durationMin * precoMin);
  }

  Future<void> _searchDestination(String query) async {
    if (query.trim().isEmpty) return;
    setState(() {
      _searchingDest = true;
      _suggestions.clear();
      _selectedDest = null;
      _estimatedDistanceKm = null;
      _estimatedDurationMin = null;
      _estimatedPrice = null;
    });
    
    try {
      final uri = Uri.parse('${ApiService.baseUrl}/gps/geocoder').replace(
        queryParameters: {'query': query}
      );
      final res = await http.get(uri, headers: ApiService.headers);
      if (res.statusCode == 200) {
        setState(() {
          _suggestions = json.decode(res.body);
        });
      }
    } catch (e) {
      print('Erro ao geocodificar: $e');
    } finally {
      setState(() {
        _searchingDest = false;
      });
    }
  }

  Future<void> _selectDestination(Map<String, dynamic> suggestion) async {
    setState(() {
      _selectedDest = suggestion;
      _destController.text = suggestion['display_name'] ?? '';
      _suggestions.clear();
    });
    await _calculateRoute();
  }

  Future<void> _calculateRoute() async {
    if (_selectedDest == null) return;
    setState(() {
      _calculatingRoute = true;
      _routePoints.clear();
      _originLatLng = null;
      _destLatLng = null;
    });
    
    try {
      final pos = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
        timeLimit: const Duration(seconds: 4),
      );
      
      final uri = Uri.parse('${ApiService.baseUrl}/gps/calcular-rota').replace(
        queryParameters: {
          'origin_lat': pos.latitude.toString(),
          'origin_lon': pos.longitude.toString(),
          'destination_lat': _selectedDest!['lat'].toString(),
          'destination_lon': _selectedDest!['lon'].toString(),
        }
      );
      
      final res = await http.get(uri, headers: ApiService.headers);
      if (res.statusCode == 200) {
        final data = json.decode(res.body);
        final dist = (data['distance_km'] as num).toDouble();
        final dur = (data['duration_minutes'] as num).toDouble();
        
        final List<LatLng> points = [];
        if (data['geometry'] != null && data['geometry']['coordinates'] != null) {
          final coords = data['geometry']['coordinates'] as List;
          for (var coord in coords) {
            if (coord is List && coord.length >= 2) {
              final double lon = (coord[0] as num).toDouble();
              final double lat = (coord[1] as num).toDouble();
              points.add(LatLng(lat, lon));
            }
          }
        }
        
        setState(() {
          _estimatedDistanceKm = dist;
          _estimatedDurationMin = dur;
          _estimatedPrice = _calculatePrice(dist, dur);
          _routePoints = points;
          _originLatLng = LatLng(pos.latitude, pos.longitude);
          _destLatLng = LatLng((_selectedDest!['lat'] as num).toDouble(), (_selectedDest!['lon'] as num).toDouble());
        });

        // Ajusta a câmera do mapa para enquadrar a rota se houver pontos
        if (points.isNotEmpty) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            try {
              // Calcula o centro e zoom aproximado para caber os pontos
              double minLat = points.first.latitude;
              double maxLat = points.first.latitude;
              double minLon = points.first.longitude;
              double maxLon = points.first.longitude;
              for (var p in points) {
                if (p.latitude < minLat) minLat = p.latitude;
                if (p.latitude > maxLat) maxLat = p.latitude;
                if (p.longitude < minLon) minLon = p.longitude;
                if (p.longitude > maxLon) maxLon = p.longitude;
              }
              final centerLat = (minLat + maxLat) / 2;
              final centerLon = (minLon + maxLon) / 2;
              _mapController.move(LatLng(centerLat, centerLon), 13.5);
            } catch (e) {
              print('Erro ao centralizar mapa: $e');
            }
          });
        }
      }
    } catch (e) {
      print('Erro ao calcular rota: $e');
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Não foi possível estimar a rota: $e')),
      );
    } finally {
      setState(() {
        _calculatingRoute = false;
      });
    }
  }

  Future<void> _abrirMapa() async {
    try {
      final pos = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
        timeLimit: const Duration(seconds: 4),
      );
      final originLat = pos.latitude;
      final originLon = pos.longitude;
      
      final String jId = widget.jornada['_id'] ?? widget.jornada['id'] ?? '';
      
      Uri url;
      if (_selectedDest != null) {
        final destLat = _selectedDest!['lat'];
        final destLon = _selectedDest!['lon'];
        url = Uri.parse('${ApiService.baseUrl}/gps/mapa-particular'
            '?origin_lat=$originLat&origin_lon=$originLon'
            '&destination_lat=$destLat&destination_lon=$destLon'
            '&jornada_id=$jId');
      } else {
        url = Uri.parse('${ApiService.baseUrl}/gps/mapa-particular'
            '?origin_lat=$originLat&origin_lon=$originLon'
            '&jornada_id=$jId');
      }
          
      if (await canLaunchUrl(url)) {
        await launchUrl(url, mode: LaunchMode.externalApplication);
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Não foi possível abrir o mapa.')),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erro ao obter localização: $e')),
      );
    }
  }

  Future<void> _abrirGoogleMaps() async {
    if (_selectedDest == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Por favor, defina um destino primeiro para abrir o Google Maps.')),
      );
      return;
    }
    try {
      final destLat = _selectedDest!['lat'];
      final destLon = _selectedDest!['lon'];
      
      final url = Uri.parse('https://www.google.com/maps/dir/?api=1&destination=$destLat,$destLon&travelmode=driving');
          
      if (await canLaunchUrl(url)) {
        await launchUrl(url, mode: LaunchMode.externalApplication);
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Não foi possível abrir o Google Maps.')),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erro ao abrir o Google Maps: $e')),
      );
    }
  }

  Future<void> _copiarTrajeto() async {
    if (_selectedDest == null) return;
    try {
      final destLat = _selectedDest!['lat'];
      final destLon = _selectedDest!['lon'];
      final link = 'https://www.google.com/maps/dir/?api=1&destination=$destLat,$destLon&travelmode=driving';
      await Clipboard.setData(ClipboardData(text: link));
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Link do trajeto copiado! Prontinho para compartilhar.'),
          backgroundColor: Colors.teal,
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erro ao copiar trajeto: $e'), backgroundColor: Colors.red),
      );
    }
  }

  Future<void> _iniciarCorrida() async {
    double kmInicio = (widget.jornada['km_inicial'] as num).toDouble();
    final list = widget.jornada['corridas_particulares'] as List?;
    if (list != null && list.isNotEmpty) {
      for (var c in list) {
        if (c['status'] == 'FINALIZADA' && c['km_fim'] != null) {
          final km = (c['km_fim'] as num).toDouble();
          if (km > kmInicio) {
            kmInicio = km;
          }
        }
      }
    }

    setState(() {
      _loading = true;
    });

    try {
      double? lat;
      double? lon;
      try {
        final pos = await Geolocator.getCurrentPosition(
          desiredAccuracy: LocationAccuracy.high,
          timeLimit: const Duration(seconds: 4),
        );
        lat = pos.latitude;
        lon = pos.longitude;
      } catch (_) {}

      final jId = widget.jornada['_id'] ?? widget.jornada['id'];
      
      final uri = Uri.parse('${ApiService.baseUrl}/jornadas/$jId/corridas-particulares/iniciar').replace(
        queryParameters: {
          'km_inicio': kmInicio.toString(),
          if (lat != null) 'localizacao_lat': lat.toString(),
          if (lon != null) 'localizacao_lon': lon.toString(),
          if (_selectedDest != null) ...{
            'destino_endereco': _selectedDest!['display_name'].toString(),
            'destino_lat': _selectedDest!['lat'].toString(),
            'destino_lon': _selectedDest!['lon'].toString(),
          }
        }
      );

      final res = await http.post(
        uri,
        headers: ApiService.headers,
      );

      if (res.statusCode == 200) {
        final body = json.decode(res.body);
        
        final updatedJornada = Map<String, dynamic>.from(widget.jornada);
        final list = List<dynamic>.from(updatedJornada['corridas_particulares'] ?? []);
        list.add(body);
        updatedJornada['corridas_particulares'] = list;
        widget.onJornadaUpdated(updatedJornada);

        setState(() {
          _activeCorrida = body;
          _kmController.clear();
          _destController.clear();
          _suggestions.clear();
          _selectedDest = null;
          _estimatedDistanceKm = null;
          _estimatedDurationMin = null;
          _estimatedPrice = null;
        });
        _startTimer();
      } else {
        final msg = json.decode(res.body)['detail'] ?? 'Erro desconhecido';
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Erro: $msg'), backgroundColor: Colors.red),
        );
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erro de conexão: $e'), backgroundColor: Colors.red),
      );
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
        });
      }
    }
  }

  Future<void> _finalizarCorrida() async {
    if (_kmController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Informe o KM final da corrida')),
      );
      return;
    }
    
    final kmFim = double.tryParse(_kmController.text);
    if (kmFim == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('KM final inválido')),
      );
      return;
    }

    final kmInicio = _activeCorrida!['km_inicio'] as num;
    if (kmFim < kmInicio) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('KM final deve ser maior ou igual ao KM inicial ($kmInicio)')),
      );
      return;
    }

    setState(() {
      _loading = true;
    });

    try {
      double? lat;
      double? lon;
      try {
        final pos = await Geolocator.getCurrentPosition(
          desiredAccuracy: LocationAccuracy.high,
          timeLimit: const Duration(seconds: 4),
        );
        lat = pos.latitude;
        lon = pos.longitude;
      } catch (_) {}

      final jId = widget.jornada['_id'] ?? widget.jornada['id'];
      final cId = _activeCorrida!['id'];

      String url = '${ApiService.baseUrl}/jornadas/$jId/corridas-particulares/$cId/finalizar?km_fim=$kmFim';
      if (lat != null && lon != null) {
        url += '&localizacao_lat=$lat&localizacao_lon=$lon';
      }

      final res = await http.post(
        Uri.parse(url),
        headers: ApiService.headers,
      );

      if (res.statusCode == 200) {
        final body = json.decode(res.body);

        final jRes = await http.get(
          Uri.parse('${ApiService.baseUrl}/jornadas/$jId'),
          headers: ApiService.headers,
        );
        if (jRes.statusCode == 200) {
          widget.onJornadaUpdated(json.decode(jRes.body));
        }

        _timer?.cancel();
        
        if (!mounted) return;
        showDialog(
          context: context,
          builder: (ctx) => AlertDialog(
            backgroundColor: const Color(0xFF1E293B),
            title: const Text('Corrida Finalizada!', style: TextStyle(color: Colors.white)),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Km Rodados: ${body['km_rodados']} km', style: const TextStyle(color: Colors.white70)),
                const SizedBox(height: 8),
                Text('Duração: ${(body['duracao_segundos'] / 60).toStringAsFixed(1)} min', style: const TextStyle(color: Colors.white70)),
                const SizedBox(height: 12),
                Text(
                  'Valor Calculado: R\$ ${body['valor_calculado'].toStringAsFixed(2)}',
                  style: const TextStyle(color: Colors.greenAccent, fontSize: 18, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            actions: [
              TextButton(
                onPressed: () {
                  Navigator.pop(ctx);
                  widget.onBack();
                },
                child: const Text('OK'),
              )
            ],
          ),
        );
        
        setState(() {
          _activeCorrida = null;
          _kmController.clear();
        });
      } else {
        final msg = json.decode(res.body)['detail'] ?? 'Erro desconhecido';
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Erro: $msg'), backgroundColor: Colors.red),
        );
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Erro de conexão: $e'), backgroundColor: Colors.red),
      );
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
        });
      }
    }
  }

  String _formatDuration(Duration d) {
    final h = d.inHours.toString().padLeft(2, '0');
    final m = (d.inMinutes % 60).toString().padLeft(2, '0');
    final s = (d.inSeconds % 60).toString().padLeft(2, '0');
    return '$h:$m:$s';
  }

  @override
  Widget build(BuildContext context) {
    final isRunning = _activeCorrida != null;

    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        title: const Text('Corrida Particular'),
        backgroundColor: const Color(0xFF1E293B),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: widget.onBack,
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Card(
                elevation: 4,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                color: const Color(0xFF1E293B),
                child: Padding(
                  padding: const EdgeInsets.all(24.0),
                  child: Column(
                    children: [
                      Icon(
                        isRunning ? Icons.play_circle_fill : Icons.stop_circle,
                        color: isRunning ? Colors.green : Colors.grey,
                        size: 64,
                      ),
                      const SizedBox(height: 16),
                      Text(
                        isRunning ? 'CORRIDA EM ANDAMENTO' : 'SEM CORRIDA ATIVA',
                        style: TextStyle(
                          color: isRunning ? Colors.green : Colors.grey,
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 1.2,
                        ),
                      ),
                      if (isRunning) ...[
                        const SizedBox(height: 24),
                        Text(
                          _formatDuration(_elapsed),
                          style: const TextStyle(
                            fontSize: 48,
                            fontWeight: FontWeight.bold,
                            fontFamily: 'monospace',
                            color: Colors.white,
                          ),
                        ),
                        const SizedBox(height: 16),
                        Text(
                          'KM Inicial: ${_activeCorrida!['km_inicio']} km',
                          style: const TextStyle(color: Colors.white70, fontSize: 16),
                        ),
                        if (_activeCorrida!['destino_endereco'] != null) ...[
                          const SizedBox(height: 8),
                          Text(
                            'Destino: ${_activeCorrida!['destino_endereco']}',
                            style: const TextStyle(color: Colors.white70, fontSize: 15),
                            textAlign: TextAlign.center,
                          ),
                          const SizedBox(height: 16),
                          Row(
                            children: [
                              Expanded(
                                child: OutlinedButton.icon(
                                  icon: const Icon(Icons.map, color: Colors.tealAccent, size: 18),
                                  label: const Text('Mapa Interno', style: TextStyle(color: Colors.white, fontSize: 13)),
                                  style: OutlinedButton.styleFrom(
                                    side: const BorderSide(color: Colors.teal),
                                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                                    padding: const EdgeInsets.symmetric(vertical: 12),
                                  ),
                                  onPressed: _abrirMapa,
                                ),
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: ElevatedButton.icon(
                                  icon: const Icon(Icons.navigation, color: Colors.white, size: 18),
                                  label: const Text('Google Maps', style: TextStyle(color: Colors.white, fontSize: 13)),
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: Colors.green,
                                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                                    padding: const EdgeInsets.symmetric(vertical: 12),
                                  ),
                                  onPressed: _abrirGoogleMaps,
                                ),
                              ),
                            ],
                          ),
                        ]
                      ]
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 32),
              
              if (_loading)
                const Center(child: CircularProgressIndicator())
              else ...[
                if (!isRunning) ...[
                  const Text(
                    'Iniciar Nova Corrida Particular',
                    style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  // KM Inicial do Hodômetro ocultado
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _destController,
                          style: const TextStyle(color: Colors.white),
                          decoration: InputDecoration(
                            labelText: 'Endereço de Destino (Opcional)',
                            labelStyle: const TextStyle(color: Colors.grey),
                            filled: true,
                            fillColor: const Color(0xFF1E293B),
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(16),
                              borderSide: BorderSide.none,
                            ),
                            prefixIcon: const Icon(Icons.map_outlined, color: Colors.tealAccent),
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      IconButton.filled(
                        icon: _searchingDest
                            ? const SizedBox(
                                width: 20,
                                height: 20,
                                child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                              )
                            : const Icon(Icons.search),
                        style: IconButton.styleFrom(backgroundColor: Colors.teal),
                        onPressed: () => _searchDestination(_destController.text),
                      ),
                    ],
                  ),
                  
                  if (_suggestions.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Container(
                      constraints: const BoxConstraints(maxHeight: 200),
                      decoration: BoxDecoration(
                        color: const Color(0xFF1E293B),
                        borderRadius: BorderRadius.circular(16),
                      ),
                      child: ListView.builder(
                        shrinkWrap: true,
                        itemCount: _suggestions.length,
                        itemBuilder: (context, index) {
                          final sug = _suggestions[index];
                          return ListTile(
                            title: Text(
                              sug['display_name'] ?? '',
                              style: const TextStyle(color: Colors.white, fontSize: 14),
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                            ),
                            onTap: () => _selectDestination(sug),
                          );
                        },
                      ),
                    ),
                  ],

                  if (_calculatingRoute)
                    const Padding(
                      padding: EdgeInsets.symmetric(vertical: 16.0),
                      child: Center(child: CircularProgressIndicator()),
                    )
                  else if (_selectedDest != null && _estimatedDistanceKm != null) ...[
                    const SizedBox(height: 16),
                    Card(
                      color: const Color(0xFF1E293B),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                      child: Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'ESTIMATIVA DA VIAGEM',
                              style: TextStyle(color: Colors.tealAccent, fontSize: 12, fontWeight: FontWeight.bold),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'Distância: ${_estimatedDistanceKm!.toStringAsFixed(2)} km',
                              style: const TextStyle(color: Colors.white, fontSize: 15),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              'Tempo Estimado: ${_estimatedDurationMin!.toStringAsFixed(1)} min',
                              style: const TextStyle(color: Colors.white, fontSize: 15),
                            ),
                            const SizedBox(height: 4),
                            if (_estimatedPrice != null)
                              Text(
                                'Preço Estimado: R\$ ${_estimatedPrice!.toStringAsFixed(2)}',
                                style: const TextStyle(color: Colors.greenAccent, fontSize: 16, fontWeight: FontWeight.bold),
                              ),
                            const SizedBox(height: 16),
                            if (_routePoints.isNotEmpty && _originLatLng != null && _destLatLng != null) ...[
                              Container(
                                height: 220,
                                margin: const EdgeInsets.only(bottom: 16),
                                decoration: BoxDecoration(
                                  borderRadius: BorderRadius.circular(12),
                                  border: Border.all(color: Colors.teal.withOpacity(0.3)),
                                ),
                                child: ClipRRect(
                                  borderRadius: BorderRadius.circular(11),
                                  child: FlutterMap(
                                    mapController: _mapController,
                                    options: MapOptions(
                                      initialCenter: _originLatLng!,
                                      initialZoom: 13,
                                      interactionOptions: const InteractionOptions(
                                        flags: InteractiveFlag.all & ~InteractiveFlag.rotate,
                                      ),
                                    ),
                                    children: [
                                      TileLayer(
                                        urlTemplate: 'https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
                                        userAgentPackageName: 'com.example.app_motorista',
                                      ),
                                      PolylineLayer(
                                        polylines: [
                                          Polyline(
                                            points: _routePoints,
                                            strokeWidth: 6,
                                            color: const Color(0xFF1A73E8), // Google Blue
                                          ),
                                        ],
                                      ),
                                      MarkerLayer(
                                        markers: [
                                          // Marcador de Origem (Círculo Verde com Borda Branca)
                                          Marker(
                                            point: _originLatLng!,
                                            width: 16,
                                            height: 16,
                                            child: Container(
                                              decoration: BoxDecoration(
                                                color: Colors.green,
                                                shape: BoxShape.circle,
                                                border: Border.all(color: Colors.white, width: 2),
                                                boxShadow: const [
                                                  BoxShadow(
                                                    color: Colors.black26,
                                                    blurRadius: 4,
                                                    offset: Offset(0, 2),
                                                  )
                                                ],
                                              ),
                                            ),
                                          ),
                                          // Marcador de Destino (Pin Vermelho estilo Google Maps)
                                          Marker(
                                            point: _destLatLng!,
                                            width: 28,
                                            height: 28,
                                            child: const Icon(
                                              Icons.location_on,
                                              color: Colors.red,
                                              size: 28,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ],
                            const Text(
                              '* Explique a estimativa ao passageiro antes de iniciar.',
                              style: TextStyle(color: Colors.amberAccent, fontSize: 12, fontStyle: FontStyle.italic),
                            ),
                            const SizedBox(height: 16),
                            Row(
                              children: [
                                Expanded(
                                  child: OutlinedButton.icon(
                                    icon: const Icon(Icons.map, color: Colors.tealAccent, size: 18),
                                    label: const Text('Mapa Interno', style: TextStyle(color: Colors.white, fontSize: 13)),
                                    style: OutlinedButton.styleFrom(
                                      side: const BorderSide(color: Colors.teal),
                                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                                      padding: const EdgeInsets.symmetric(vertical: 12),
                                    ),
                                    onPressed: _abrirMapa,
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: ElevatedButton.icon(
                                    icon: const Icon(Icons.navigation, color: Colors.white, size: 18),
                                    label: const Text('Google Maps', style: TextStyle(color: Colors.white, fontSize: 13)),
                                    style: ElevatedButton.styleFrom(
                                      backgroundColor: Colors.green,
                                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                                      padding: const EdgeInsets.symmetric(vertical: 12),
                                    ),
                                    onPressed: _abrirGoogleMaps,
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 8),
                            SizedBox(
                              width: double.infinity,
                              child: ElevatedButton.icon(
                                icon: const Icon(Icons.share, color: Colors.white, size: 18),
                                label: const Text('Compartilhar Trajeto (Copiar Link)', style: TextStyle(color: Colors.white, fontSize: 13)),
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: Colors.indigoAccent,
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                                  padding: const EdgeInsets.symmetric(vertical: 12),
                                ),
                                onPressed: _copiarTrajeto,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],

                  const SizedBox(height: 24),
                  SizedBox(
                    height: 56,
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.blueAccent,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                      ),
                      onPressed: _iniciarCorrida,
                      child: const Text(
                        'INICIAR CORRIDA AGORA',
                        style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.white),
                      ),
                    ),
                  ),
                ] else ...[
                  const Text(
                    'Finalizar Corrida Particular',
                    style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: _kmController,
                    keyboardType: TextInputType.number,
                    style: const TextStyle(color: Colors.white),
                    decoration: InputDecoration(
                      labelText: 'KM Final do Hodômetro',
                      labelStyle: const TextStyle(color: Colors.grey),
                      filled: true,
                      fillColor: const Color(0xFF1E293B),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(16),
                        borderSide: BorderSide.none,
                      ),
                      prefixIcon: const Icon(Icons.speed, color: Colors.redAccent),
                    ),
                  ),
                  const SizedBox(height: 24),
                  SizedBox(
                    height: 56,
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.redAccent,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                      ),
                      onPressed: _finalizarCorrida,
                      child: const Text(
                        'FINALIZAR CORRIDA',
                        style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.white),
                      ),
                    ),
                  ),
                ]
              ]
            ],
          ),
        ),
      ),
    );
  }
}

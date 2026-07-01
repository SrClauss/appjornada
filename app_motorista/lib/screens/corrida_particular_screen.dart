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
import 'package:flutter_tts/flutter_tts.dart';

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

  // Navegação interna por voz
  bool _navigatingInternally = false;
  List<dynamic> _navigationSteps = [];
  int _currentStepIndex = 0;
  StreamSubscription<Position>? _gpsStreamSubscription;
  double _currentHeading = 0.0;
  LatLng? _currentLatLng;
  final FlutterTts _flutterTts = FlutterTts();
  String _lastSpokenText = "";
  double _distanceToNextStep = 0.0;

  // Timer para corrida ativa
  Timer? _timer;
  Duration _elapsed = Duration.zero;
  Timer? _pollingTimer;


  Future<void> _initTts() async {
    try {
      await _flutterTts.setLanguage("pt-BR");
      await _flutterTts.setSpeechRate(0.5);
      await _flutterTts.setVolume(1.0);
      await _flutterTts.setPitch(1.0);
    } catch (e) {
      print("Erro ao inicializar TTS: $e");
    }
  }

  Future<void> _initCurrentLocation() async {
    try {
      final pos = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
        timeLimit: const Duration(seconds: 4),
      );
      if (mounted) {
        setState(() {
          _originLatLng = LatLng(pos.latitude, pos.longitude);
        });
        _mapController.move(_originLatLng!, 14.0);
      }
    } catch (e) {
      print('Erro ao obter localizacao inicial: $e');
      final list = widget.jornada['historico_gps'] as List?;
      if (list != null && list.isNotEmpty) {
        final lastPoint = list.last;
        final lat = (lastPoint['lat'] as num).toDouble();
        final lon = (lastPoint['lon'] as num).toDouble();
        if (mounted) {
          setState(() {
            _originLatLng = LatLng(lat, lon);
          });
          _mapController.move(_originLatLng!, 14.0);
        }
      }
    }
  }

  Future<void> _onMapTap(LatLng position) async {
    if (_activeCorrida != null || _loading || _calculatingRoute) return;

    setState(() {
      _searchingDest = true;
      _suggestions.clear();
      _selectedDest = null;
      _estimatedDistanceKm = null;
      _estimatedDurationMin = null;
      _estimatedPrice = null;
      _destLatLng = position;
    });

    try {
      final uri = Uri.parse('${ApiService.baseUrl}/gps/reverse').replace(
        queryParameters: {
          'lat': position.latitude.toString(),
          'lon': position.longitude.toString(),
        }
      );
      final res = await http.get(uri, headers: ApiService.headers);
      if (res.statusCode == 200) {
        final data = json.decode(res.body);
        setState(() {
          _selectedDest = {
            'display_name': data['display_name'] ?? 'Ponto no Mapa',
            'lat': position.latitude,
            'lon': position.longitude,
          };
          _destController.text = data['display_name'] ?? 'Ponto no Mapa';
        });
        await _calculateRoute();
      } else {
        setState(() {
          _selectedDest = {
            'display_name': 'Ponto selecionado (${position.latitude.toStringAsFixed(4)}, ${position.longitude.toStringAsFixed(4)})',
            'lat': position.latitude,
            'lon': position.longitude,
          };
          _destController.text = _selectedDest!['display_name'];
        });
        await _calculateRoute();
      }
    } catch (e) {
      print('Erro ao reverter coordenadas: $e');
      setState(() {
        _selectedDest = {
          'display_name': 'Ponto selecionado (${position.latitude.toStringAsFixed(4)}, ${position.longitude.toStringAsFixed(4)})',
          'lat': position.latitude,
          'lon': position.longitude,
        };
        _destController.text = _selectedDest!['display_name'];
      });
      await _calculateRoute();
    } finally {
      setState(() {
        _searchingDest = false;
      });
    }
  }

  @override
  void initState() {
    super.initState();
    _initTts();
    _initCurrentLocation();
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
    _gpsStreamSubscription?.cancel();
    _flutterTts.stop();
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

  int _secondsCount = 0;
  void _startTimer() {
    if (_activeCorrida == null) return;
    final startStr = _activeCorrida!['horario_inicio'];
    if (startStr != null) {
      final startDt = DateTime.parse(startStr).toLocal();
      _timer?.cancel();
      _secondsCount = 0;
      _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
        if (!mounted) return;
        setState(() {
          _elapsed = DateTime.now().difference(startDt);
        });

        _secondsCount++;
        if (_secondsCount >= 10) {
          _secondsCount = 0;
          _checkArrival();
        }
      });
    }
  }

  Future<void> _checkArrival() async {
    if (_activeCorrida == null || _loading) return;
    final destCoords = _activeCorrida!['destino_coordenadas'];
    if (destCoords == null) return;
    
    final double? destLat = destCoords['lat'] != null ? (destCoords['lat'] as num).toDouble() : null;
    final double? destLon = destCoords['lon'] != null ? (destCoords['lon'] as num).toDouble() : null;
    if (destLat == null || destLon == null) return;

    try {
      final pos = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
        timeLimit: const Duration(seconds: 3),
      );
      
      final distanceInMeters = Geolocator.distanceBetween(
        pos.latitude,
        pos.longitude,
        destLat,
        destLon,
      );
      
      print('[AutoArrival] Distancia do destino: $distanceInMeters metros');
      if (distanceInMeters <= 50) {
        print('[AutoArrival] Chegou ao destino! Encerrando automaticamente...');
        _timer?.cancel();
        _finalizarCorrida();
      }
    } catch (e) {
      print('Erro ao verificar chegada automatica: $e');
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
      Position? pos;
      try {
        pos = await Geolocator.getCurrentPosition(
          desiredAccuracy: LocationAccuracy.high,
          timeLimit: const Duration(seconds: 4),
        );
      } catch (e) {
        print('Erro no high accuracy GPS: $e. Tentando last known...');
        try {
          pos = await Geolocator.getLastKnownPosition();
        } catch (_) {}
        if (pos == null) {
          try {
            pos = await Geolocator.getCurrentPosition(
              desiredAccuracy: LocationAccuracy.low,
              timeLimit: const Duration(seconds: 3),
            );
          } catch (_) {}
        }
      }

      double lat;
      double lon;
      if (pos != null) {
        lat = pos.latitude;
        lon = pos.longitude;
      } else {
        final list = widget.jornada['historico_gps'] as List?;
        if (list != null && list.isNotEmpty) {
          final lastPoint = list.last;
          lat = (lastPoint['lat'] as num).toDouble();
          lon = (lastPoint['lon'] as num).toDouble();
        } else {
          lat = -18.7144;
          lon = -39.8280;
        }
      }
      
      final uri = Uri.parse('${ApiService.baseUrl}/gps/calcular-rota').replace(
        queryParameters: {
          'origin_lat': lat.toString(),
          'origin_lon': lon.toString(),
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
        
        final steps = data['steps'] as List? ?? [];

        setState(() {
          _estimatedDistanceKm = dist;
          _estimatedDurationMin = dur;
          _estimatedPrice = _calculatePrice(dist, dur);
          _routePoints = points;
          _navigationSteps = steps;
          _originLatLng = LatLng(lat, lon);
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

  void _stopInternalNavigation() {
    _gpsStreamSubscription?.cancel();
    _flutterTts.stop();
    setState(() {
      _navigatingInternally = false;
    });
  }

  void _processNavigationSteps(Position position) {
    if (_navigationSteps.isEmpty) return;
    
    if (_currentStepIndex >= _navigationSteps.length) {
      return;
    }
    
    int nextIndex = _currentStepIndex + 1;
    if (nextIndex < _navigationSteps.length) {
      final nextStep = _navigationSteps[nextIndex];
      final double nextLat = (nextStep['lat'] as num).toDouble();
      final double nextLon = (nextStep['lon'] as num).toDouble();
      
      final distance = Geolocator.distanceBetween(
        position.latitude,
        position.longitude,
        nextLat,
        nextLon,
      );
      
      setState(() {
        _distanceToNextStep = distance;
      });
      
      if (distance < 30) {
        _currentStepIndex = nextIndex;
        final newStep = _navigationSteps[nextIndex];
        final String instr = newStep['instruction'] ?? "";
        _speak(instr);
      } else if (distance <= 150 && distance > 100) {
        final String instr = nextStep['instruction'] ?? "";
        final String alertText = "Em cento e trinta metros, $instr";
        if (_lastSpokenText != alertText) {
          _speak(alertText);
        }
      }
    } else {
      final double destLat = _destLatLng?.latitude ?? 0.0;
      final double destLon = _destLatLng?.longitude ?? 0.0;
      if (destLat != 0.0) {
        final distance = Geolocator.distanceBetween(
          position.latitude,
          position.longitude,
          destLat,
          destLon,
        );
        setState(() {
          _distanceToNextStep = distance;
        });
        if (distance < 30) {
          _speak("Você chegou ao seu destino.");
          _currentStepIndex = _navigationSteps.length;
        }
      }
    }
  }

  Future<void> _speak(String text) async {
    if (text.isEmpty) return;
    _lastSpokenText = text;
    try {
      await _flutterTts.speak(text);
    } catch (e) {
      print("Erro no TTS: $e");
    }
  }

  Widget _buildNavigationUI() {
    final nextStepIndex = _currentStepIndex + 1;
    final hasNextStep = nextStepIndex < _navigationSteps.length;
    final currentStep = _navigationSteps.isNotEmpty && _currentStepIndex < _navigationSteps.length
        ? _navigationSteps[_currentStepIndex]
        : null;
    final nextStep = hasNextStep ? _navigationSteps[nextStepIndex] : null;

    final String instructionText = nextStep != null
        ? "Em ${_distanceToNextStep.toStringAsFixed(0)}m, ${nextStep['instruction']}"
        : (currentStep != null ? currentStep['instruction'] : "Siga a rota no mapa");

    IconData maneuverIcon = Icons.navigation;
    if (nextStep != null) {
      final mod = nextStep['modifier'] as String? ?? '';
      if (mod.contains('left')) {
        maneuverIcon = Icons.turn_left;
      } else if (mod.contains('right')) {
        maneuverIcon = Icons.turn_right;
      } else if (mod.contains('uturn')) {
        maneuverIcon = Icons.u_turn_left;
      }
    }

    return Scaffold(
      body: Stack(
        children: [
          FlutterMap(
            mapController: _mapController,
            options: MapOptions(
              initialCenter: _currentLatLng ?? _originLatLng ?? const LatLng(-18.7144, -39.8280),
              initialZoom: 17.5,
              initialRotation: -_currentHeading,
            ),
            children: [
              TileLayer(
                urlTemplate: 'https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
                userAgentPackageName: 'com.srclauss.appjornada.app_motorista',
              ),
              PolylineLayer(
                polylines: [
                  Polyline(
                    points: _routePoints,
                    strokeWidth: 7.0,
                    color: const Color(0xFF1A73E8),
                  ),
                ],
              ),
              MarkerLayer(
                markers: [
                  if (_destLatLng != null)
                    Marker(
                      point: _destLatLng!,
                      width: 40,
                      height: 40,
                      child: const Icon(
                        Icons.location_on,
                        color: Colors.red,
                        size: 40,
                      ),
                    ),
                  Marker(
                    point: _currentLatLng ?? _originLatLng ?? const LatLng(-18.7144, -39.8280),
                    width: 60,
                    height: 60,
                    child: Transform.rotate(
                      angle: _currentHeading * (3.141592653589793 / 180),
                      child: const Icon(
                        Icons.navigation,
                        color: Colors.tealAccent,
                        size: 45,
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
          Positioned(
            top: MediaQuery.of(context).padding.top + 16,
            left: 16,
            right: 16,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              decoration: BoxDecoration(
                color: const Color(0xE61E293B),
                borderRadius: BorderRadius.circular(16),
                boxShadow: const [
                  BoxShadow(
                    color: Colors.black45,
                    blurRadius: 10,
                    offset: Offset(0, 4),
                  )
                ],
                border: Border.all(color: Colors.teal.withOpacity(0.5), width: 1.5),
              ),
              child: Row(
                children: [
                  CircleAvatar(
                    backgroundColor: Colors.teal,
                    radius: 24,
                    child: Icon(maneuverIcon, color: Colors.white, size: 28),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          instructionText,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        if (nextStep != null && nextStep['street'] != null && nextStep['street'].toString().isNotEmpty) ...[
                          const SizedBox(height: 4),
                          Text(
                            "Entrar na: ${nextStep['street']}",
                            style: const TextStyle(
                              color: Colors.white70,
                              fontSize: 13,
                            ),
                          ),
                        ]
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          Positioned(
            bottom: 24,
            left: 16,
            right: 16,
            child: Row(
              children: [
                FloatingActionButton(
                  heroTag: 'exit_nav',
                  backgroundColor: Colors.redAccent,
                  onPressed: _stopInternalNavigation,
                  child: const Icon(Icons.close, color: Colors.white),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
                    decoration: BoxDecoration(
                      color: const Color(0xE61E293B),
                      borderRadius: BorderRadius.circular(16),
                      boxShadow: const [
                        BoxShadow(
                          color: Colors.black45,
                          blurRadius: 10,
                          offset: Offset(0, -4),
                        )
                      ],
                      border: Border.all(color: Colors.white12, width: 1.0),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Text(
                              "DISTÂNCIA RESTANTE",
                              style: TextStyle(color: Colors.white38, fontSize: 10, fontWeight: FontWeight.bold),
                            ),
                            Text(
                              _estimatedDistanceKm != null ? "${_estimatedDistanceKm!.toStringAsFixed(1)} km" : "--",
                              style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                            ),
                          ],
                        ),
                        Container(width: 1, height: 30, color: Colors.white12),
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Text(
                              "TEMPO RESTANTE",
                              style: TextStyle(color: Colors.white38, fontSize: 10, fontWeight: FontWeight.bold),
                            ),
                            Text(
                              _estimatedDurationMin != null ? "${_estimatedDurationMin!.toStringAsFixed(0)} min" : "--",
                              style: const TextStyle(color: Colors.tealAccent, fontSize: 18, fontWeight: FontWeight.bold),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _abrirGoogleMapsComCorrida(Map activeCorrida) async {
    final destCoords = activeCorrida['destino_coordenadas'];
    if (destCoords == null) return;
    try {
      final destLat = destCoords['lat'];
      final destLon = destCoords['lon'];
      if (destLat == null || destLon == null) return;
      
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
    double kmInicio = 0.0;
    if (widget.jornada['km_inicial'] != null) {
      kmInicio = (widget.jornada['km_inicial'] as num).toDouble();
    }
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
        _abrirGoogleMapsComCorrida(body);
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

  Future<void> _finalizarCorrida({String? justificativa}) async {
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

      String url = '${ApiService.baseUrl}/jornadas/$jId/corridas-particulares/$cId/finalizar';
      final List<String> params = [];
      if (justificativa != null && justificativa.isNotEmpty) {
        params.add('justificativa=${Uri.encodeComponent(justificativa)}');
      }
      if (lat != null && lon != null) {
        params.add('localizacao_lat=$lat');
        params.add('localizacao_lon=$lon');
      }
      if (params.isNotEmpty) {
        url += '?' + params.join('&');
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
        
        setState(() {
          _activeCorrida = null;
          _kmController.clear();
        });

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
                if (justificativa != null && justificativa.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Text('Justificativa: $justificativa', style: const TextStyle(color: Colors.amberAccent, fontSize: 13)),
                ]
              ],
            ),
            actions: [
              TextButton(
                onPressed: () {
                  Navigator.pop(ctx);
                  widget.onBack();
                },
                child: const Text('OK', style: TextStyle(color: Colors.tealAccent)),
              )
            ],
          ),
        );
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

  Future<void> _finalizarComJustificativa() async {
    final TextEditingController justifController = TextEditingController();
    await showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1E293B),
        title: const Text('Justificativa de Término', style: TextStyle(color: Colors.white)),
        content: TextField(
          controller: justifController,
          autofocus: true,
          style: const TextStyle(color: Colors.white),
          decoration: const InputDecoration(
            hintText: 'Digite o motivo do término antecipado...',
            hintStyle: TextStyle(color: Colors.grey),
            focusedBorder: UnderlineInputBorder(borderSide: BorderSide(color: Colors.tealAccent)),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Cancelar', style: TextStyle(color: Colors.grey)),
          ),
          TextButton(
            onPressed: () {
              Navigator.of(ctx).pop();
              _finalizarCorrida(justificativa: justifController.text);
            },
            child: const Text('Finalizar', style: TextStyle(color: Colors.tealAccent)),
          ),
        ],
      ),
    );
  }

  String _formatDuration(Duration d) {
    final h = d.inHours.toString().padLeft(2, '0');
    final m = (d.inMinutes % 60).toString().padLeft(2, '0');
    final s = (d.inSeconds % 60).toString().padLeft(2, '0');
    return '$h:$m:$s';
  }

  @override
  Widget build(BuildContext context) {
    if (_navigatingInternally) {
      return _buildNavigationUI();
    }
    final isRunning = _activeCorrida != null;

    if (isRunning) {
      return Scaffold(
        backgroundColor: const Color(0xFF0F172A),
        appBar: AppBar(
          title: const Text('Viagem em Andamento', style: TextStyle(fontWeight: FontWeight.bold)),
          backgroundColor: const Color(0xFF1E293B),
          leading: IconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: widget.onBack,
          ),
        ),
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Card(
                  elevation: 6,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
                  color: const Color(0xFF1E293B),
                  child: Padding(
                    padding: const EdgeInsets.all(24.0),
                    child: Column(
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Container(
                              width: 10,
                              height: 10,
                              decoration: const BoxDecoration(
                                color: Colors.tealAccent,
                                shape: BoxShape.circle,
                              ),
                            ),
                            const SizedBox(width: 8),
                            const Text(
                              'EM VIAGEM (GOOGLE MAPS)',
                              style: TextStyle(
                                color: Colors.tealAccent,
                                fontSize: 13,
                                fontWeight: FontWeight.bold,
                                letterSpacing: 1.5,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 24),
                        Text(
                          _formatDuration(_elapsed),
                          style: const TextStyle(
                            fontSize: 52,
                            fontWeight: FontWeight.bold,
                            fontFamily: 'monospace',
                            color: Colors.white,
                          ),
                        ),
                        const SizedBox(height: 16),
                        const Divider(color: Colors.white10),
                        const SizedBox(height: 16),
                        if (_activeCorrida!['destino_endereco'] != null) ...[
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Icon(Icons.location_on, color: Colors.redAccent, size: 24),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    const Text(
                                      'DESTINO',
                                      style: TextStyle(color: Colors.grey, fontSize: 11, fontWeight: FontWeight.bold),
                                    ),
                                    const SizedBox(height: 4),
                                    Text(
                                      '${_activeCorrida!['destino_endereco']}',
                                      style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w500),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ],
                        const SizedBox(height: 16),
                        Text(
                          'KM Inicial: ${_activeCorrida!['km_inicio']} km',
                          style: const TextStyle(color: Colors.white38, fontSize: 13),
                        ),
                      ],
                    ),
                  ),
                ),
                const Spacer(),
                if (_loading)
                  const Center(child: CircularProgressIndicator())
                else ...[
                  SizedBox(
                    height: 56,
                    child: ElevatedButton.icon(
                      icon: const Icon(Icons.check_circle_outline, color: Colors.white),
                      label: const Text(
                        'FINALIZAR VIAGEM',
                        style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.white),
                      ),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.teal,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                      ),
                      onPressed: () => _finalizarCorrida(),
                    ),
                  ),
                  const SizedBox(height: 12),
                  SizedBox(
                    height: 56,
                    child: OutlinedButton.icon(
                      icon: const Icon(Icons.cancel_outlined, color: Colors.redAccent),
                      label: const Text(
                        'ENCERRAR ANTES (JUSTIFICAR)',
                        style: TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: Colors.redAccent),
                      ),
                      style: OutlinedButton.styleFrom(
                        side: const BorderSide(color: Colors.redAccent, width: 1.5),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                      ),
                      onPressed: _finalizarComJustificativa,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      );
    }

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
              Container(
                height: 320,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: Colors.teal.withOpacity(0.3), width: 1.5),
                  boxShadow: const [
                    BoxShadow(
                      color: Colors.black26,
                      blurRadius: 8,
                      offset: Offset(0, 4),
                    )
                  ],
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(15),
                  child: Stack(
                    children: [
                      FlutterMap(
                        mapController: _mapController,
                        options: MapOptions(
                          initialCenter: _originLatLng ?? const LatLng(-18.7144, -39.8280),
                          initialZoom: 14,
                          onTap: (tapPosition, point) => _onMapTap(point),
                          interactionOptions: const InteractionOptions(
                            flags: InteractiveFlag.all & ~InteractiveFlag.rotate,
                          ),
                        ),
                        children: [
                          TileLayer(
                            urlTemplate: 'https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}',
                            userAgentPackageName: 'com.srclauss.appjornada.app_motorista',
                          ),
                          if (_routePoints.isNotEmpty)
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
                              if (_originLatLng != null)
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
                              if (_destLatLng != null)
                                Marker(
                                  point: _destLatLng!,
                                  width: 32,
                                  height: 32,
                                  child: const Icon(
                                    Icons.location_on,
                                    color: Colors.red,
                                    size: 32,
                                  ),
                                ),
                            ],
                          ),
                        ],
                      ),
                      Positioned(
                        top: 12,
                        left: 12,
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                          decoration: BoxDecoration(
                            color: const Color(0xCC0F172A),
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(color: Colors.tealAccent.withOpacity(0.5)),
                          ),
                          child: const Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.touch_app, color: Colors.tealAccent, size: 14),
                              SizedBox(width: 6),
                              Text(
                                'Toque no mapa para definir o destino',
                                style: TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w500),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),
              
              if (_loading)
                const Center(child: CircularProgressIndicator())
              else ...[
                const Text(
                  'Iniciar Nova Corrida Particular',
                  style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
                ),
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

                          const Text(
                            '* Explique a estimativa ao passageiro antes de iniciar.',
                            style: TextStyle(color: Colors.amberAccent, fontSize: 12, fontStyle: FontStyle.italic),
                          ),
                          const SizedBox(height: 16),
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
              ]
            ],
          ),
        ),
      ),
    );
  }
}

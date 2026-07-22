import 'dart:async';
import 'dart:convert';
import 'dart:ui';
import 'package:flutter/foundation.dart';
import 'package:flutter_background_service/flutter_background_service.dart';
import 'package:flutter_background_service_android/flutter_background_service_android.dart';
import 'package:geolocator/geolocator.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:app_motorista/core/api_service.dart';
import 'package:app_motorista/core/overlay_service.dart';

// Callback executado em um isolate Dart separado (Background Process)
@pragma('vm:entry-point')
void onStart(ServiceInstance service) async {
  DartPluginRegistrant.ensureInitialized();

  StreamSubscription<Position>? positionSubscription;
  String? currentJornadaId;
  Position? lastPosition;
  List<Map<String, dynamic>> pendingPoints = [];
  DateTime? lastBatchSentTime;
  Position? inactivityRefPosition;
  DateTime? inactivityRefTime;
  bool isAutoPaused = false;

  // Se o serviço for Android, configura eventos específicos
  if (service is AndroidServiceInstance) {
    service.on('setAsForeground').listen((event) {
      service.setAsForegroundService();
    });

    service.on('setAsBackground').listen((event) {
      service.setAsBackgroundService();
    });
  }

  service.on('stopService').listen((event) {
    positionSubscription?.cancel();
    service.stopSelf();
  });

  // Função para ler o estado do SharedPreferences e iniciar ou parar o GPS
  Future<void> syncTrackingState() async {
    final prefs = await SharedPreferences.getInstance();
    final jornadaId = prefs.getString('jornada_id');
    final token = prefs.getString('token');
    final baseUrl = prefs.getString('api_url') ?? defaultApiUrl;
    final motoristaId = prefs.getString('motorista_id');

    if (jornadaId == null || token == null || motoristaId == null) {
      if (positionSubscription != null) {
        positionSubscription?.cancel();
        positionSubscription = null;
        currentJornadaId = null;
      }
      print('[BackgroundService] Rastreamento cancelado: sem jornada ativa ou credenciais.');
      service.stopSelf();
      return;
    }

    // Se já estiver rodando para a mesma jornada, não faz nada
    if (positionSubscription != null && currentJornadaId == jornadaId) {
      return;
    }

    // Limpa rastreamento anterior se houver
    positionSubscription?.cancel();
    currentJornadaId = jornadaId;
    lastPosition = null;
    pendingPoints.clear();
    lastBatchSentTime = null;
    inactivityRefPosition = null;
    inactivityRefTime = DateTime.now();
    isAutoPaused = false;

    int tempoInatividadeMinutos = prefs.getInt('tempo_inatividade_minutos') ?? 25;
    double raioMudancaMetros = prefs.getDouble('raio_mudanca_metros') ?? 30.0;

    try {
      final cfgRes = await http.get(
        Uri.parse('$baseUrl/config/inatividade'),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer $token',
        },
      );
      if (cfgRes.statusCode == 200) {
        final cfgData = json.decode(cfgRes.body);
        if (cfgData['tempo_inatividade_minutos'] != null) {
          tempoInatividadeMinutos = (cfgData['tempo_inatividade_minutos'] as num).toInt();
          await prefs.setInt('tempo_inatividade_minutos', tempoInatividadeMinutos);
        }
        if (cfgData['raio_mudanca_metros'] != null) {
          raioMudancaMetros = (cfgData['raio_mudanca_metros'] as num).toDouble();
          await prefs.setDouble('raio_mudanca_metros', raioMudancaMetros);
        }
      }
    } catch (_) {}

    print('[BackgroundService] Iniciando monitoramento GPS para jornada: $jornadaId (Inatividade: $tempoInatividadeMinutos min / $raioMudancaMetros m)');

    if (service is AndroidServiceInstance) {
      service.setForegroundNotificationInfo(
        title: "Jornada em Andamento",
        content: "Enviando telemetria em segundo plano.",
      );
    }

    // Configuração de localização em segundo plano
    LocationSettings locationSettings;
    if (defaultTargetPlatform == TargetPlatform.android) {
      locationSettings = AndroidSettings(
        accuracy: LocationAccuracy.high,
        distanceFilter: 0,
        intervalDuration: const Duration(seconds: 1), // Coleta a cada 1 segundo
        foregroundNotificationConfig: const ForegroundNotificationConfig(
          notificationText: "Rastreando localização da jornada em segundo plano.",
          notificationTitle: "Jornada em Andamento",
          enableWakeLock: true,
        ),
      );
    } else {
      locationSettings = const LocationSettings(
        accuracy: LocationAccuracy.high,
        distanceFilter: 0,
      );
    }

    // Envia ponto de localização inicial imediatamente
    try {
      final pos = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
        timeLimit: const Duration(seconds: 5),
      );
      final point = {
        'timestamp': DateTime.now().toUtc().toIso8601String(),
        'localizacao': {
          'type': 'Point',
          'coordinates': [pos.longitude, pos.latitude],
        },
        'distancia_ultima_m': 0.0,
        'status': pos.speed > 0.8 ? 'CONDUZINDO' : 'PARADO',
      };
      pendingPoints.add(point);
      lastPosition = pos;
      inactivityRefPosition = pos;
      inactivityRefTime = DateTime.now();
      
      final success = await _sendBatchBackground(baseUrl, token, motoristaId, jornadaId, [point]);
      if (success) {
        pendingPoints.clear();
      }
      lastBatchSentTime = DateTime.now();
    } catch (e) {
      print('[BackgroundService] Erro no ponto inicial: $e');
    }

    // Escuta o fluxo de GPS continuamente
    positionSubscription = Geolocator.getPositionStream(locationSettings: locationSettings)
        .listen((Position pos) async {
      final agora = DateTime.now();
      
      double distance = 0.0;
      final localLastPos = lastPosition;
      if (localLastPos != null) {
        distance = Geolocator.distanceBetween(
          localLastPos.latitude,
          localLastPos.longitude,
          pos.latitude,
          pos.longitude,
        );
      }
      lastPosition = pos;

      // --- Monitoramento de Inatividade (configurável) ---
      if (!isAutoPaused) {
        if (inactivityRefPosition == null) {
          inactivityRefPosition = pos;
          inactivityRefTime = agora;
        } else {
          final distRef = Geolocator.distanceBetween(
            inactivityRefPosition!.latitude,
            inactivityRefPosition!.longitude,
            pos.latitude,
            pos.longitude,
          );
          if (distRef > raioMudancaMetros) {
            inactivityRefPosition = pos;
            inactivityRefTime = agora;
          } else {
            final elapsedSec = agora.difference(inactivityRefTime!).inSeconds;
            final limitSec = tempoInatividadeMinutos * 60;
            if (elapsedSec >= limitSec) {
              isAutoPaused = true;
              print('[BackgroundService] Inatividade detectada (>= $tempoInatividadeMinutos min sem deslocamento >${raioMudancaMetros}m). Disparando pausa.');
              _trigarPausaInatividade(baseUrl, token, jornadaId, pos);
            }
          }
        }
      }

      final status = pos.speed > 0.8 ? 'CONDUZINDO' : 'PARADO';
      final point = {
        'timestamp': agora.toUtc().toIso8601String(),
        'localizacao': {
          'type': 'Point',
          'coordinates': [pos.longitude, pos.latitude],
        },
        'distancia_ultima_m': distance,
        'status': status,
      };
      pendingPoints.add(point);

      // Envia em lote a cada 15 segundos
      if (lastBatchSentTime == null || agora.difference(lastBatchSentTime!).inSeconds >= 15) {
        lastBatchSentTime = agora;
        final pointsToSend = List<Map<String, dynamic>>.from(pendingPoints);
        final success = await _sendBatchBackground(baseUrl, token, motoristaId, jornadaId, pointsToSend);
        if (success) {
          pendingPoints.removeWhere((p) => pointsToSend.contains(p));
        }
      }
    });
  }

  // Sincroniza o estado ao iniciar o serviço
  await syncTrackingState();

  // Escuta sinais da UI principal para ressincronizar
  service.on('syncState').listen((event) async {
    await syncTrackingState();
  });
}

// Envia batch de localizações para o backend
Future<bool> _sendBatchBackground(
  String baseUrl,
  String token,
  String motoristaId,
  String jornadaId,
  List<Map<String, dynamic>> points,
) async {
  if (points.isEmpty) return true;
  try {
    final body = {
      'motorista_id': motoristaId,
      'jornada_id': jornadaId,
      'pontos': points,
    };

    final response = await http.post(
      Uri.parse('$baseUrl/gps/batch'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
      body: json.encode(body),
    );

    if (response.statusCode == 201 || response.statusCode == 200) {
      print('[BackgroundService] Batch de ${points.length} pontos GPS enviado com sucesso.');
      return true;
    } else {
      print('[BackgroundService] Erro no envio do batch (${response.statusCode}): ${response.body}');
      return false;
    }
  } catch (e) {
    print('[BackgroundService] Exceção ao enviar batch de localização: $e');
    return false;
  }
}

Future<void> _trigarPausaInatividade(String baseUrl, String token, String jornadaId, Position pos) async {
  try {
    final uri = Uri.parse('$baseUrl/jornadas/$jornadaId/pausas?tipo=PAUSA_INATIVIDADE&localizacao_lat=${pos.latitude}&localizacao_lon=${pos.longitude}');
    await http.post(
      uri,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $token',
      },
    );
  } catch (e) {
    print('[BackgroundService] Erro ao enviar requisição de pausa por inatividade: $e');
  }

  await OverlayService.showInactivityNotification();
}

// Ponto de entrada executado no iOS em segundo plano
@pragma('vm:entry-point')
Future<bool> onIosBackground(ServiceInstance service) async {
  return true;
}

class GpsService {
  static bool isRunning = false;

  // Configura e inicializa o serviço de plano de fundo
  static Future<void> initializeService() async {
    final service = FlutterBackgroundService();

    await service.configure(
      androidConfiguration: AndroidConfiguration(
        onStart: onStart,
        autoStart: false, // Só iniciamos quando a jornada for aberta
        autoStartOnBoot: false,
        isForegroundMode: true,
        notificationChannelId: 'gps_telemetria_channel',
        initialNotificationTitle: 'Rastreamento de Jornada',
        initialNotificationContent: 'Aguardando telemetria...',
        foregroundServiceNotificationId: 8888,
      ),
      iosConfiguration: IosConfiguration(
        autoStart: false,
        onForeground: onStart,
        onBackground: onIosBackground,
      ),
    );
  }

  // Solicita as permissões necessárias para o GPS
  static Future<bool> requestPermissions() async {
    bool serviceEnabled;
    LocationPermission permission;

    serviceEnabled = await Geolocator.isLocationServiceEnabled();
    if (!serviceEnabled) {
      return false;
    }

    permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied) {
        return false;
      }
    }
    
    if (permission == LocationPermission.deniedForever) {
      return false;
    }

    return true;
  }

  // Inicia o rastreamento em segundo plano persistente
  static Future<void> startTracking(String jornadaId) async {
    final prefs = await SharedPreferences.getInstance();
    final currentJornadaId = prefs.getString('jornada_id');
    if (isRunning && currentJornadaId == jornadaId) {
      print('[GpsService] Rastreamento já ativo para a jornada $jornadaId.');
      return;
    }

    final hasPerm = await requestPermissions();
    if (!hasPerm) {
      print('[GpsService] Permissão de GPS negada.');
      return;
    }

    // Salva o estado atual no SharedPreferences para o isolate ler
    await prefs.setString('jornada_id', jornadaId);
    if (ApiService.token != null) {
      await prefs.setString('token', ApiService.token!);
    }
    if (ApiService.motoristaId != null) {
      await prefs.setString('motorista_id', ApiService.motoristaId!);
    }
    await prefs.setString('api_url', ApiService.baseUrl);

    isRunning = true;

    // Inicializa/Inicia o serviço nativo
    final service = FlutterBackgroundService();
    final serviceRunning = await service.isRunning();
    if (!serviceRunning) {
      await service.startService();
    } else {
      service.invoke('syncState');
    }

    print('[GpsService] Rastreamento em segundo plano iniciado para jornada $jornadaId.');
    OverlayService.startOverlay();
  }

  // Para o rastreamento periódico e o serviço de background
  static Future<void> stopTracking() async {
    final prefs = await SharedPreferences.getInstance();
    if (!isRunning && prefs.getString('jornada_id') == null) {
      return;
    }

    await prefs.remove('jornada_id');
    isRunning = false;

    // Envia sinal para o serviço parar
    final service = FlutterBackgroundService();
    final serviceRunning = await service.isRunning();
    if (serviceRunning) {
      service.invoke('stopService');
    }

    print('[GpsService] Rastreamento parado.');
    OverlayService.stopOverlay();
  }
}

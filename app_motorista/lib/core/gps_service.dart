import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:geolocator/geolocator.dart';
import 'package:http/http.dart' as http;
import 'package:app_motorista/core/api_service.dart';

class GpsService {
  static StreamSubscription<Position>? _positionSubscription;
  static Position? _lastPosition;
  static DateTime? _lastSentTime;
  static bool isRunning = false;

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

  // Inicia o rastreamento periódico em segundo plano se a jornada estiver ativa
  static Future<void> startTracking(String jornadaId) async {
    if (isRunning) return;

    final hasPerm = await requestPermissions();
    if (!hasPerm) {
      print('[GpsService] Permissão de GPS negada.');
      return;
    }

    isRunning = true;
    _lastPosition = null;
    _lastSentTime = null;

    // Enviar ponto inicial imediatamente
    await _sendCurrentLocation(jornadaId);

    // Configurações do geolocator para segundo plano
    LocationSettings locationSettings;
    if (defaultTargetPlatform == TargetPlatform.android) {
      locationSettings = AndroidSettings(
        accuracy: LocationAccuracy.high,
        distanceFilter: 0,
        intervalDuration: const Duration(seconds: 15),
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

    _positionSubscription = Geolocator.getPositionStream(locationSettings: locationSettings)
        .listen((Position pos) async {
      final agora = DateTime.now();
      // Throttle de envio: evita sobrecarga, limitando a 12 segundos mínimos entre envios
      if (_lastSentTime == null || agora.difference(_lastSentTime!).inSeconds >= 12) {
        _lastSentTime = agora;
        await _sendLocation(jornadaId, pos);
      }
    });

    print('[GpsService] Rastreamento em segundo plano iniciado para a jornada $jornadaId.');
  }

  // Envia a localização atual para a API
  static Future<void> _sendLocation(String jornadaId, Position pos) async {
    try {
      double distance = 0.0;
      if (_lastPosition != null) {
        distance = Geolocator.distanceBetween(
          _lastPosition!.latitude,
          _lastPosition!.longitude,
          pos.latitude,
          pos.longitude,
        );
      }

      _lastPosition = pos;

      // Status do motorista baseado na velocidade (m/s)
      // Se velocidade > 0.8 m/s (~3 km/h) -> CONDUZINDO, senão PARADO
      final status = pos.speed > 0.8 ? 'CONDUZINDO' : 'PARADO';

      final body = {
        'motorista_id': ApiService.motoristaId,
        'jornada_id': jornadaId,
        'localizacao': {
          'type': 'Point',
          'coordinates': [pos.longitude, pos.latitude], // [longitude, latitude]
        },
        'distancia_ultima_m': distance,
        'status': status,
      };

      final response = await http.post(
        Uri.parse('${ApiService.baseUrl}/gps'),
        headers: ApiService.headers,
        body: json.encode(body),
      );

      if (response.statusCode == 201) {
        print('[GpsService] Ponto GPS enviado com sucesso: [${pos.latitude}, ${pos.longitude}], status: $status, dist: ${distance.toStringAsFixed(1)}m');
      } else {
        print('[GpsService] Erro ao enviar ponto GPS (${response.statusCode}): ${response.body}');
      }
    } catch (e) {
      print('[GpsService] Erro ao obter/enviar localização: $e');
    }
  }

  static Future<void> _sendCurrentLocation(String jornadaId) async {
    try {
      final pos = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
        timeLimit: const Duration(seconds: 5),
      );
      await _sendLocation(jornadaId, pos);
    } catch (e) {
      print('[GpsService] Erro no ponto inicial: $e');
    }
  }

  // Para o rastreamento periódico
  static void stopTracking() {
    _positionSubscription?.cancel();
    _positionSubscription = null;
    isRunning = false;
    _lastPosition = null;
    _lastSentTime = null;
    print('[GpsService] Rastreamento parado.');
  }
}

import 'dart:async';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_background_service/flutter_background_service.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:geolocator/geolocator.dart';
import 'package:permission_handler/permission_handler.dart';

const String _kApiBaseUrl = String.fromEnvironment(
  'API_BASE_URL',
  defaultValue: 'http://10.0.2.2:8000',
);

const String _kGpsJornadaId = 'gps_jornada_id';
const String _kGpsMotoristaId = 'gps_motorista_id';

/// Manages GPS tracking in a background service during an active jornada.
class GpsBackgroundService {
  GpsBackgroundService._();

  /// Must be called once before [runApp] to configure the background service.
  static Future<void> initialize() async {
    final service = FlutterBackgroundService();
    await service.configure(
      androidConfiguration: AndroidConfiguration(
        onStart: _onStart,
        autoStart: false,
        isForegroundMode: true,
        notificationChannelId: 'gps_jornada_channel',
        initialNotificationTitle: 'App Jornada',
        initialNotificationContent: 'Rastreamento GPS ativo',
        foregroundServiceNotificationId: 888,
      ),
      iosConfiguration: IosConfiguration(
        autoStart: false,
        onForeground: _onStart,
        onBackground: _onIosBackground,
      ),
    );
  }

  /// Shows a dialog explaining background location usage, requests the
  /// permission, and then starts GPS tracking for [jornadaId].
  static Future<void> startTracking(
    BuildContext context, {
    required String jornadaId,
    required String motoristaId,
  }) async {
    final granted = await _ensureBackgroundLocationPermission(context);
    if (!granted) return;

    const storage = FlutterSecureStorage();
    await storage.write(key: _kGpsJornadaId, value: jornadaId);
    await storage.write(key: _kGpsMotoristaId, value: motoristaId);

    await FlutterBackgroundService().startService();
  }

  /// Signals the background service to stop sending GPS points (jornada paused).
  static void pauseTracking() =>
      FlutterBackgroundService().invoke('pause');

  /// Signals the background service to resume sending GPS points.
  static void resumeTracking() =>
      FlutterBackgroundService().invoke('resume');

  /// Stops the background service and clears persisted tracking data.
  static Future<void> stopTracking() async {
    FlutterBackgroundService().invoke('stopService');
    const storage = FlutterSecureStorage();
    await storage.delete(key: _kGpsJornadaId);
    await storage.delete(key: _kGpsMotoristaId);
  }

  // ---------------------------------------------------------------------------
  // Internal helpers
  // ---------------------------------------------------------------------------

  static Future<bool> _ensureBackgroundLocationPermission(
    BuildContext context,
  ) async {
    // First ensure foreground location is granted.
    var locStatus = await Permission.location.status;
    if (!locStatus.isGranted) {
      locStatus = await Permission.location.request();
      if (!locStatus.isGranted) return false;
    }

    // Check if background location is already granted.
    final bgStatus = await Permission.locationAlways.status;
    if (bgStatus.isGranted) return true;

    // Show rationale before requesting background location.
    if (context.mounted) {
      final proceed = await showDialog<bool>(
        context: context,
        barrierDismissible: false,
        builder: (_) => AlertDialog(
          title: const Text('Permissão de localização em segundo plano'),
          content: const Text(
            'O App Jornada precisa acessar sua localização mesmo com a tela '
            'desligada para registrar o trajeto completo da jornada.\n\n'
            'Na próxima tela, selecione "Permitir o tempo todo" para ativar '
            'o rastreamento em segundo plano.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Não permitir'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Continuar'),
            ),
          ],
        ),
      );
      if (proceed != true) return false;
    }

    final result = await Permission.locationAlways.request();
    return result.isGranted;
  }
}

// -----------------------------------------------------------------------------
// Background isolate entry points (must be top-level / @pragma annotated)
// -----------------------------------------------------------------------------

@pragma('vm:entry-point')
Future<bool> _onIosBackground(ServiceInstance service) async {
  return true;
}

@pragma('vm:entry-point')
void _onStart(ServiceInstance service) async {
  const storage = FlutterSecureStorage();

  final jornadaId = await storage.read(key: _kGpsJornadaId);
  final motoristaId = await storage.read(key: _kGpsMotoristaId);

  String? activeJornadaId = jornadaId;
  String? activeMotoristaId = motoristaId;
  bool isPaused = false;
  Timer? timer;

  Future<void> sendGpsPoint() async {
    if (isPaused || activeJornadaId == null || activeMotoristaId == null) {
      return;
    }
    try {
      final permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) return;

      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          timeLimit: Duration(seconds: 10),
        ),
      );

      final token = await storage.read(key: 'jwt_token');
      if (token == null) return;

      final dio = Dio(BaseOptions(
        baseUrl: _kApiBaseUrl,
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 15),
      ));

      await dio.post(
        '/gps/',
        data: {
          'motorista_id': activeMotoristaId,
          'jornada_id': activeJornadaId,
          'lat': position.latitude,
          'lon': position.longitude,
          'timestamp': DateTime.now().toUtc().toIso8601String(),
        },
        options: Options(
          headers: {'Authorization': 'Bearer $token'},
          contentType: 'application/json',
        ),
      );
    } catch (_) {
      // GPS errors are silently ignored to avoid disrupting the driver.
    }
  }

  // Start the 15-second periodic timer.
  sendGpsPoint();
  timer = Timer.periodic(const Duration(seconds: 15), (_) => sendGpsPoint());

  service.on('pause').listen((_) => isPaused = true);
  service.on('resume').listen((_) => isPaused = false);

  service.on('stopService').listen((_) async {
    timer?.cancel();
    service.stopSelf();
  });
}

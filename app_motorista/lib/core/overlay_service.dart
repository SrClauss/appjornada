import 'package:flutter/services.dart';
import 'package:app_motorista/core/api_service.dart';

class OverlayService {
  static const _channel = MethodChannel('com.srclauss.appjornada/overlay');
  static bool _initialized = false;
  static Function(Map<String, dynamic>)? onRevisionRequest;
  static Function()? onPausaInatividadeRequest;

  static void initialize() {
    if (_initialized) return;
    _initialized = true;

    _channel.setMethodCallHandler((call) async {
      if (call.method == 'onScreenshotCaptured') {
        if (call.arguments is String) {
          final String filePath = call.arguments as String;
          await _handleScreenshotCaptured(filePath);
        } else if (call.arguments is Map) {
          final Map<String, dynamic> data = Map<String, dynamic>.from(call.arguments as Map);
          await _handleScreenshotCapturedMap(data);
        }
      } else if (call.method == 'onNavigateToRevision') {
        final Map<dynamic, dynamic> data = call.arguments as Map<dynamic, dynamic>;
        if (onRevisionRequest != null) {
          onRevisionRequest!(Map<String, dynamic>.from(data));
        }
      } else if (call.method == 'onNavigateToPausaInatividade') {
        if (onPausaInatividadeRequest != null) {
          onPausaInatividadeRequest!();
        }
      }
    });
  }

  static Future<bool> startOverlay() async {
    initialize();
    try {
      final result = await _channel.invokeMethod<bool>('startOverlay');
      if (result == true) {
        print("[OverlayService] Bolinha flutuante iniciada.");
        return true;
      }
    } on PlatformException catch (e) {
      print("[OverlayService] Erro ao iniciar bolinha flutuante: $e");
    }
    return false;
  }

  static Future<bool> stopOverlay() async {
    try {
      final result = await _channel.invokeMethod<bool>('stopOverlay');
      if (result == true) {
        print("[OverlayService] Bolinha flutuante desativada.");
        return true;
      }
    } catch (e) {
      print("[OverlayService] Erro ao parar bolinha: $e");
    }
    return false;
  }

  static Future<void> clearWarning() async {
    try {
      await _channel.invokeMethod('clearWarning');
    } catch (e) {
      print("[OverlayService] Erro ao limpar aviso: $e");
    }
  }

  static Future<Map<String, dynamic>?> getPendingRevision() async {
    try {
      final res = await _channel.invokeMethod<Map<dynamic, dynamic>>('getPendingRevision');
      if (res != null) {
        return Map<String, dynamic>.from(res);
      }
    } catch (e) {
      print("[OverlayService] Erro ao obter revisão pendente: $e");
    }
    return null;
  }

  static Future<void> showInactivityNotification() async {
    try {
      await _channel.invokeMethod('showInactivityNotification');
    } catch (e) {
      print("[OverlayService] Erro ao exibir notificação de inatividade: $e");
    }
  }

  static Future<bool> getPendingPausaInatividade() async {
    try {
      final res = await _channel.invokeMethod<bool>('getPendingPausaInatividade');
      return res ?? false;
    } catch (e) {
      print("[OverlayService] Erro ao verificar pausa por inatividade pendente: $e");
    }
    return false;
  }

  static Future<void> _handleScreenshotCaptured(String filePath) async {
    print("[OverlayService] Print capturado em: $filePath. Enviando comprovante...");

    try {
      final res = await ApiService.uploadAndProcessComprovante(filePath);
      if (res != null) {
        print("[OverlayService] Comprovante enviado e processado com sucesso!");
        
        final String? plataforma = res['plataforma'];
        final dynamic valorRaw = res['valor_extraido'];
        final String? origem = res['origem'];
        final String? destino = res['destino'];
        final String? url = res['url_comprovante'];

        double valor = 0.0;
        if (valorRaw is num) {
          valor = valorRaw.toDouble();
        } else if (valorRaw is String) {
          valor = double.tryParse(valorRaw) ?? 0.0;
        }

        bool isIncompleto = false;
        if (plataforma == null || plataforma == 'OUTROS' || valor <= 0.0 || origem == null || origem.isEmpty || destino == null || destino.isEmpty) {
          isIncompleto = true;
        }

        if (isIncompleto) {
          print("[OverlayService] Comprovante incompleto detectado. Exibindo alerta de revisão.");
          await _channel.invokeMethod('showWarningNotification', {
            'filePath': filePath,
            'plataforma': plataforma ?? '99',
            'valor': valor,
            'origem': origem ?? '',
            'destino': destino ?? '',
            'url_comprovante': url ?? '',
          });
        }
      } else {
        print("[OverlayService] Falha ao processar comprovante no servidor.");
      }
    } catch (e) {
      print("[OverlayService] Exceção ao processar print capturado: $e");
    }
  }

  static Future<void> _handleScreenshotCapturedMap(Map<String, dynamic> data) async {
    final String filePath = data['filePath'];
    final bool isRideRecord = data['isRideRecord'] ?? false;
    
    if (!isRideRecord) {
      await _handleScreenshotCaptured(filePath);
      return;
    }
    
    print("[OverlayService] Print de Corrida Gravada recebido. Enviando para o servidor...");
    
    final double startLat = data['startLat'] ?? 0.0;
    final double startLon = data['startLon'] ?? 0.0;
    final double endLat = data['endLat'] ?? 0.0;
    final double endLon = data['endLon'] ?? 0.0;
    final int startTime = data['startTime'] ?? 0;
    final int endTime = data['endTime'] ?? 0;
    final List<dynamic> routePointsDynamic = data['routePoints'] ?? [];
    
    final List<Map<String, double>> routePoints = routePointsDynamic.map((item) {
      final map = Map<dynamic, dynamic>.from(item as Map);
      return {
        'lat': (map['lat'] as num).toDouble(),
        'lon': (map['lon'] as num).toDouble(),
      };
    }).toList();

    try {
      final res = await ApiService.uploadAndProcessComprovante(
        filePath,
        startLat: startLat,
        startLon: startLon,
        endLat: endLat,
        endLon: endLon,
        startTime: startTime,
        endTime: endTime,
        routePoints: routePoints,
      );
      
      if (res != null) {
        print("[OverlayService] Corrida gravada enviada com sucesso!");
        final String? plataforma = res['plataforma'];
        final dynamic valorRaw = res['valor_extraido'];
        final String? origem = res['origem'];
        final String? destino = res['destino'];
        final String? url = res['url_comprovante'];

        double valor = 0.0;
        if (valorRaw is num) {
          valor = valorRaw.toDouble();
        } else if (valorRaw is String) {
          valor = double.tryParse(valorRaw) ?? 0.0;
        }

        bool isIncompleto = false;
        if (plataforma == null || plataforma == 'OUTROS' || valor <= 0.0) {
          isIncompleto = true;
        }

        if (isIncompleto) {
          print("[OverlayService] Comprovante incompleto detectado. Exibindo alerta de revisão.");
          await _channel.invokeMethod('showWarningNotification', {
            'filePath': filePath,
            'plataforma': plataforma ?? '99',
            'valor': valor,
            'origem': origem ?? '',
            'destino': destino ?? '',
            'url_comprovante': url ?? '',
          });
        }
      } else {
        print("[OverlayService] Falha ao processar comprovante de corrida gravada no servidor.");
      }
    } catch (e) {
      print("[OverlayService] Exceção ao processar corrida gravada: $e");
    }
  }
}

import 'package:flutter/services.dart';
import 'package:app_motorista/core/api_service.dart';

class OverlayService {
  static const _channel = MethodChannel('com.srclauss.appjornada/overlay');
  static bool _initialized = false;

  static void initialize() {
    if (_initialized) return;
    _initialized = true;

    _channel.setMethodCallHandler((call) async {
      if (call.method == 'onScreenshotCaptured') {
        final String filePath = call.arguments as String;
        await _handleScreenshotCaptured(filePath);
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

  static Future<void> _handleScreenshotCaptured(String filePath) async {
    print("[OverlayService] Print capturado em: $filePath. Enviando comprovante...");

    try {
      // Faz o upload e processamento do comprovante na jornada aberta
      final res = await ApiService.uploadAndProcessComprovante(filePath);
      if (res != null) {
        print("[OverlayService] Comprovante enviado e processado com sucesso!");
      } else {
        print("[OverlayService] Falha ao processar comprovante no servidor.");
      }
    } catch (e) {
      print("[OverlayService] Exceção ao processar print capturado: $e");
    }
  }
}

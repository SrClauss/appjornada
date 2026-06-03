import 'dart:async';
import 'package:flutter/services.dart';

class AccessibilityServiceHelper {
  // Nome do canal correspondente ao configurado no Kotlin
  static const EventChannel _eventChannel = EventChannel('com.example.myapp/accessibility');
  
  StreamSubscription? _subscription;

  /// Inicia a escuta dos eventos enviados do lado Nativo.
  /// A função de callback [onEventReceived] receberá um mapa contendo:
  /// - 'packageName': o ID do pacote do app onde o evento ocorreu.
  /// - 'className': a classe do componente visual de onde o evento se originou.
  /// - 'eventType': a string representando o tipo do evento (ex: TYPE_VIEW_CLICKED, TYPE_WINDOW_STATE_CHANGED).
  /// - 'texts': lista de strings de todos os textos encontrados na tela no momento do evento.
  void startListening(Function(Map<String, dynamic>) onEventReceived) {
    _subscription = _eventChannel.receiveBroadcastStream().listen((dynamic event) {
      if (event is Map) {
        final Map<String, dynamic> data = Map<String, dynamic>.from(event);
        onEventReceived(data);
      }
    }, onError: (dynamic error) {
      print('Erro ao receber evento de acessibilidade: $error');
    });
  }

  /// Cancela a assinatura do stream para liberar recursos.
  void stopListening() {
    _subscription?.cancel();
    _subscription = null;
  }
}

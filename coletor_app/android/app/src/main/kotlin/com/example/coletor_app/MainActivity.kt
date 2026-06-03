package com.example.coletor_app

import android.content.Intent
import android.provider.Settings
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodChannel

class MainActivity: FlutterActivity() {
    private val ACCESSIBILITY_CHANNEL = "com.example.myapp/accessibility"
    private val UTILS_CHANNEL = "com.example.myapp/utils"

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        
        // Registra o EventChannel para escuta dos logs em tempo real
        EventChannel(flutterEngine.dartExecutor.binaryMessenger, ACCESSIBILITY_CHANNEL)
            .setStreamHandler(AccessibilityStreamHandler)

        // Registra o MethodChannel para abrir as configurações de acessibilidade do sistema
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, UTILS_CHANNEL).setMethodCallHandler { call, result ->
            if (call.method == "openAccessibilitySettings") {
                try {
                    val intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)
                    intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK
                    startActivity(intent)
                    result.success(true)
                } catch (e: Exception) {
                    result.error("UNAVAILABLE", "Não foi possível abrir as configurações de acessibilidade", e.message)
                }
            } else {
                result.notImplemented()
            }
        }
    }
}

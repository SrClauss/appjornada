package com.example.myapp

import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.EventChannel

class MainActivity: FlutterActivity() {
    private val ACCESSIBILITY_CHANNEL = "com.example.myapp/accessibility"

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        
        // Registra o EventChannel utilizando nosso StreamHandler singleton
        EventChannel(flutterEngine.dartExecutor.binaryMessenger, ACCESSIBILITY_CHANNEL)
            .setStreamHandler(AccessibilityStreamHandler)
    }
}

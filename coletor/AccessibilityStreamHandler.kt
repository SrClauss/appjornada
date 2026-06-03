package com.example.myapp

import android.os.Handler
import android.os.Looper
import io.flutter.plugin.common.EventChannel

object AccessibilityStreamHandler : EventChannel.StreamHandler {
    
    @Volatile
    private var eventSink: EventChannel.EventSink? = null
    
    // Handler vinculado ao loop principal (UI Thread)
    private val mainHandler = Handler(Looper.getMainLooper())

    override fun onListen(arguments: Any?, events: EventChannel.EventSink?) {
        synchronized(this) {
            this.eventSink = events
        }
    }

    override fun onCancel(arguments: Any?) {
        synchronized(this) {
            this.eventSink = null
        }
    }

    /**
     * Envia o payload de acessibilidade de forma segura e síncrona com o loop principal do Flutter.
     */
    fun sendEvent(data: Map<String, Any?>) {
        mainHandler.post {
            synchronized(this) {
                eventSink?.success(data)
            }
        }
    }
}

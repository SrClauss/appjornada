package com.example.coletor_app

import android.os.Handler
import android.os.Looper
import io.flutter.plugin.common.EventChannel

object AccessibilityStreamHandler : EventChannel.StreamHandler {
    
    @Volatile
    private var eventSink: EventChannel.EventSink? = null
    
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

    fun sendEvent(data: Map<String, Any?>) {
        mainHandler.post {
            synchronized(this) {
                eventSink?.success(data)
            }
        }
    }
}

package com.srclauss.appjornada.app_motorista

import android.app.Activity
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.media.projection.MediaProjectionManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {

    private val CHANNEL = "com.srclauss.appjornada/overlay"
    private val REQUEST_OVERLAY_PERMISSION = 1001
    private val REQUEST_SCREEN_CAPTURE = 1002
    private var methodChannelResult: MethodChannel.Result? = null

    private val screenshotReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            if (intent?.action == OverlayBubbleService.ACTION_SCREENSHOT_CAPTURED) {
                val filePath = intent.getStringExtra(OverlayBubbleService.EXTRA_FILE_PATH)
                if (filePath != null) {
                    flutterEngine?.dartExecutor?.binaryMessenger?.let { messenger ->
                        MethodChannel(messenger, CHANNEL).invokeMethod("onScreenshotCaptured", filePath)
                    }
                }
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        createNotificationChannel()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(
                screenshotReceiver,
                IntentFilter(OverlayBubbleService.ACTION_SCREENSHOT_CAPTURED),
                Context.RECEIVER_NOT_EXPORTED
            )
        } else {
            registerReceiver(
                screenshotReceiver,
                IntentFilter(OverlayBubbleService.ACTION_SCREENSHOT_CAPTURED)
            )
        }
    }

    override fun onDestroy() {
        unregisterReceiver(screenshotReceiver)
        super.onDestroy()
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL).setMethodCallHandler { call, result ->
            when (call.method) {
                "startOverlay" -> {
                    if (OverlayBubbleService.isServiceRunning) {
                        result.success(true)
                    } else {
                        methodChannelResult = result
                        checkAndRequestOverlayPermission()
                    }
                }
                "stopOverlay" -> {
                    stopOverlayService()
                    result.success(true)
                }
                "isOverlayRunning" -> {
                    result.success(OverlayBubbleService.isServiceRunning)
                }
                else -> {
                    result.notImplemented()
                }
            }
        }
    }

    private fun checkAndRequestOverlayPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && !Settings.canDrawOverlays(this)) {
            val intent = Intent(
                Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                Uri.parse("package:$packageName")
            )
            startActivityForResult(intent, REQUEST_OVERLAY_PERMISSION)
        } else {
            requestScreenCapture()
        }
    }

    private fun requestScreenCapture() {
        val mediaProjectionManager = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        startActivityForResult(mediaProjectionManager.createScreenCaptureIntent(), REQUEST_SCREEN_CAPTURE)
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)

        if (requestCode == REQUEST_OVERLAY_PERMISSION) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && Settings.canDrawOverlays(this)) {
                requestScreenCapture()
            } else {
                methodChannelResult?.error("PERMISSION_DENIED", "Overlay permission not granted", null)
                methodChannelResult = null
            }
        }

        if (requestCode == REQUEST_SCREEN_CAPTURE) {
            if (resultCode == Activity.RESULT_OK && data != null) {
                startOverlayService(resultCode, data)
                methodChannelResult?.success(true)
            } else {
                methodChannelResult?.error("CAPTURE_DENIED", "Screen capture permission not granted", null)
            }
            methodChannelResult = null
        }
    }

    private fun startOverlayService(resultCode: Int, resultData: Intent) {
        val serviceIntent = Intent(this, OverlayBubbleService::class.java).apply {
            action = OverlayBubbleService.ACTION_START
            putExtra(OverlayBubbleService.EXTRA_RESULT_CODE, resultCode)
            putExtra(OverlayBubbleService.EXTRA_RESULT_DATA, resultData)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(serviceIntent)
        } else {
            startService(serviceIntent)
        }
    }

    private fun stopOverlayService() {
        val serviceIntent = Intent(this, OverlayBubbleService::class.java).apply {
            action = OverlayBubbleService.ACTION_STOP
        }
        stopService(serviceIntent)
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val name = "Rastreamento de Jornada"
            val descriptionText = "Canal de notificação para rastreamento de localização"
            val importance = NotificationManager.IMPORTANCE_LOW
            val channel = NotificationChannel("gps_telemetria_channel", name, importance).apply {
                description = descriptionText
            }
            val notificationManager: NotificationManager =
                getSystemService(NotificationManager::class.java)
            notificationManager.createNotificationChannel(channel)
        }
    }
}

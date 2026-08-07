package com.srclauss.appjornada.app_motorista

import android.app.Activity
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.media.projection.MediaProjectionConfig
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
    private val REQUEST_VIDEO_RECORD_CAPTURE = 1003
    private var methodChannelResult: MethodChannel.Result? = null

    private val screenshotReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            if (intent?.action == OverlayBubbleService.ACTION_SCREENSHOT_CAPTURED) {
                val filePath = intent.getStringExtra(OverlayBubbleService.EXTRA_FILE_PATH)
                if (filePath != null) {
                    val isRideRecord = intent.getBooleanExtra("is_ride_record", false)
                    val data = mutableMapOf<String, Any>(
                        "filePath" to filePath,
                        "isRideRecord" to isRideRecord
                    )
                    if (isRideRecord) {
                        data["startLat"] = intent.getDoubleExtra("start_lat", 0.0)
                        data["startLon"] = intent.getDoubleExtra("start_lon", 0.0)
                        data["endLat"] = intent.getDoubleExtra("end_lat", 0.0)
                        data["endLon"] = intent.getDoubleExtra("end_lon", 0.0)
                        data["startTime"] = intent.getLongExtra("start_time", 0L)
                        data["endTime"] = intent.getLongExtra("end_time", 0L)
                        
                        val routeList = mutableListOf<Map<String, Double>>()
                        val routeArray = intent.getDoubleArrayExtra("route_points")
                        if (routeArray != null) {
                            for (i in 0 until routeArray.size / 2) {
                                routeList.add(mapOf("lat" to routeArray[i * 2], "lon" to routeArray[i * 2 + 1]))
                            }
                        }
                        data["routePoints"] = routeList
                    }
                    
                    flutterEngine?.dartExecutor?.binaryMessenger?.let { messenger ->
                        MethodChannel(messenger, CHANNEL).invokeMethod("onScreenshotCaptured", data)
                    }
                }
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        createNotificationChannel()
        handleIntent(intent)

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

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleIntent(intent)
    }

    private fun handleIntent(intent: Intent?) {
        if (intent != null && intent.hasExtra("action")) {
            val action = intent.getStringExtra("action")
            if (action == "revisar_comprovante") {
                val filePath = intent.getStringExtra("filePath")
                val plataforma = intent.getStringExtra("plataforma")
                val valor = intent.getDoubleExtra("valor", 0.0)
                val origem = intent.getStringExtra("origem")
                val destino = intent.getStringExtra("destino")
                
                val data = mapOf(
                    "filePath" to filePath,
                    "plataforma" to plataforma,
                    "valor" to valor,
                    "origem" to origem,
                    "destino" to destino
                )
                pendingRevision = data
                
                flutterEngine?.dartExecutor?.binaryMessenger?.let { messenger ->
                    MethodChannel(messenger, CHANNEL).invokeMethod("onNavigateToRevision", data)
                }
            } else if (action == "pausa_inatividade") {
                pendingPausaInatividade = true
                flutterEngine?.dartExecutor?.binaryMessenger?.let { messenger ->
                    MethodChannel(messenger, CHANNEL).invokeMethod("onNavigateToPausaInatividade", null)
                }
            } else if (action == "start_native_video") {
                val mediaProjectionManager = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
                startActivityForResult(mediaProjectionManager.createScreenCaptureIntent(), REQUEST_VIDEO_RECORD_CAPTURE)
            }
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
                "showWarningNotification" -> {
                    val arguments = call.arguments as? Map<*, *>
                    val filePath = arguments?.get("filePath") as? String
                    val plataforma = arguments?.get("plataforma") as? String
                    val valor = arguments?.get("valor") as? Double
                    val origem = arguments?.get("origem") as? String
                    val destino = arguments?.get("destino") as? String
                    
                    showWarningNotification(filePath, plataforma, valor, origem, destino)
                    
                    val serviceIntent = Intent(this, OverlayBubbleService::class.java).apply {
                        action = "ACTION_SET_WARNING"
                        putExtra("warning_active", true)
                        putExtra("filePath", filePath)
                        putExtra("plataforma", plataforma)
                        putExtra("valor", valor ?: 0.0)
                        putExtra("origem", origem)
                        putExtra("destino", destino)
                    }
                    startService(serviceIntent)
                    result.success(true)
                }
                "clearWarning" -> {
                    val serviceIntent = Intent(this, OverlayBubbleService::class.java).apply {
                        action = "ACTION_SET_WARNING"
                        putExtra("warning_active", false)
                    }
                    startService(serviceIntent)
                    result.success(true)
                }
                "getPendingRevision" -> {
                    result.success(pendingRevision)
                    pendingRevision = null
                }
                "showInactivityNotification" -> {
                    showInactivityNotification()
                    val serviceIntent = Intent(this, OverlayBubbleService::class.java).apply {
                        action = "ACTION_SET_WARNING"
                        putExtra("warning_active", true)
                        putExtra("warning_type", "PAUSA_INATIVIDADE")
                    }
                    startService(serviceIntent)
                    result.success(true)
                }
                "getPendingPausaInatividade" -> {
                    result.success(pendingPausaInatividade)
                    pendingPausaInatividade = false
                }
                "startNativeVideoRecorder" -> {
                    methodChannelResult = result
                    val mediaProjectionManager = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
                    val intent = if (Build.VERSION.SDK_INT >= 34) {
                        val config = MediaProjectionConfig.createConfigForUserChoice()
                        mediaProjectionManager.createScreenCaptureIntent(config)
                    } else {
                        mediaProjectionManager.createScreenCaptureIntent()
                    }
                    startActivityForResult(intent, REQUEST_VIDEO_RECORD_CAPTURE)
                }
                "stopNativeVideoRecorder" -> {
                    val serviceIntent = Intent(this, NativeVideoRecorderService::class.java).apply {
                        action = NativeVideoRecorderService.ACTION_STOP
                    }
                    startService(serviceIntent)
                    stopOverlayService()
                    val path = NativeVideoRecorderService.lastOutputFile
                    result.success(path)
                }
                "getLastRecordedVideo" -> {
                    val path = NativeVideoRecorderService.lastOutputFile
                    result.success(path)
                }
                "clearLastRecordedVideo" -> {
                    NativeVideoRecorderService.clearLastOutputFile()
                    result.success(true)
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
                moveTaskToBack(true)
                methodChannelResult?.success(true)
            } else {
                methodChannelResult?.error("CAPTURE_DENIED", "Screen capture permission not granted", null)
            }
            methodChannelResult = null
        }

        if (requestCode == REQUEST_VIDEO_RECORD_CAPTURE) {
            if (resultCode == Activity.RESULT_OK && data != null) {
                val serviceIntent = Intent(this, NativeVideoRecorderService::class.java).apply {
                    action = NativeVideoRecorderService.ACTION_START
                    putExtra(NativeVideoRecorderService.EXTRA_RESULT_CODE, resultCode)
                    putExtra(NativeVideoRecorderService.EXTRA_RESULT_DATA, data)
                }
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    startForegroundService(serviceIntent)
                } else {
                    startService(serviceIntent)
                }
                startOverlayService(resultCode, data)
                moveTaskToBack(true)
                methodChannelResult?.success(true)
            } else {
                methodChannelResult?.error("CAPTURE_DENIED", "Permissão de gravação de tela negada", null)
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
    private fun showWarningNotification(
        filePath: String?,
        plataforma: String?,
        valor: Double?,
        origem: String?,
        destino: String?
    ) {
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        
        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra("action", "revisar_comprovante")
            putExtra("filePath", filePath)
            putExtra("plataforma", plataforma)
            putExtra("valor", valor ?: 0.0)
            putExtra("origem", origem)
            putExtra("destino", destino)
        }
        
        val pendingIntent = android.app.PendingIntent.getActivity(
            this,
            2002,
            intent,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M)
                android.app.PendingIntent.FLAG_UPDATE_CURRENT or android.app.PendingIntent.FLAG_IMMUTABLE
            else
                android.app.PendingIntent.FLAG_UPDATE_CURRENT
        )
        
        val channelId = "gps_telemetria_channel"
        val notification = androidx.core.app.NotificationCompat.Builder(this, channelId)
            .setContentTitle("Revisão de Comprovante")
            .setContentText("Alguns dados do print não foram identificados. Clique para revisar.")
            .setSmallIcon(android.R.drawable.stat_notify_chat)
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)
            .build()
            
        notificationManager.notify(2003, notification)
    }

    private fun showInactivityNotification() {
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        
        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_SINGLE_TOP or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra("action", "pausa_inatividade")
        }
        
        val pendingIntent = android.app.PendingIntent.getActivity(
            this,
            2004,
            intent,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M)
                android.app.PendingIntent.FLAG_UPDATE_CURRENT or android.app.PendingIntent.FLAG_IMMUTABLE
            else
                android.app.PendingIntent.FLAG_UPDATE_CURRENT
        )
        
        val channelId = "gps_telemetria_channel"
        val notification = androidx.core.app.NotificationCompat.Builder(this, channelId)
            .setContentTitle("Jornada Pausada por Inatividade")
            .setContentText("Você ficou sem se movimentar por 25 minutos. Sua jornada foi pausada.")
            .setSmallIcon(android.R.drawable.stat_notify_chat)
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)
            .build()
            
        notificationManager.notify(2004, notification)
    }

    override fun onResume() {
        super.onResume()
        if (OverlayBubbleService.isServiceRunning) {
            val serviceIntent = Intent(this, OverlayBubbleService::class.java).apply {
                action = "ACTION_SET_VISIBLE"
                putExtra("visible", false)
            }
            startService(serviceIntent)
        }
    }

    override fun onPause() {
        super.onPause()
        if (OverlayBubbleService.isServiceRunning) {
            val serviceIntent = Intent(this, OverlayBubbleService::class.java).apply {
                action = "ACTION_SET_VISIBLE"
                putExtra("visible", true)
            }
            startService(serviceIntent)
        }
    }

    companion object {
        var pendingRevision: Map<String, Any?>? = null
        var pendingPausaInatividade: Boolean = false
    }
}

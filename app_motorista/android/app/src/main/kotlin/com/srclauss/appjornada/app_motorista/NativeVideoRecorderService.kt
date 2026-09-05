package com.srclauss.appjornada.app_motorista

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.MediaRecorder
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.util.DisplayMetrics
import android.view.WindowManager
import androidx.core.app.NotificationCompat
import java.io.File

class NativeVideoRecorderService : Service() {

    companion object {
        const val ACTION_START = "ACTION_START"
        const val ACTION_STOP = "ACTION_STOP"
        const val EXTRA_RESULT_CODE = "EXTRA_RESULT_CODE"
        const val EXTRA_RESULT_DATA = "EXTRA_RESULT_DATA"
        
        var isRecording = false
            private set
        var lastOutputFile: String? = null
            private set

        fun clearLastOutputFile() {
            lastOutputFile = null
        }
    }

    private var mediaProjection: MediaProjection? = null
    private var virtualDisplay: VirtualDisplay? = null
    private var mediaRecorder: MediaRecorder? = null
    private var currentOutputFile: File? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val action = intent?.action
        if (action == ACTION_START) {
            val resultCode = intent.getIntExtra(EXTRA_RESULT_CODE, 0)
            val resultData = intent.getParcelableExtra<Intent>(EXTRA_RESULT_DATA)
            if (resultCode != 0 && resultData != null) {
                startForegroundServiceNotification()
                startRecording(resultCode, resultData)
            } else {
                stopSelf()
            }
        } else if (action == ACTION_STOP) {
            stopRecordingInternal()
            stopSelf()
        }
        return START_NOT_STICKY
    }

    private fun startForegroundServiceNotification() {
        val channelId = "native_video_recorder_channel"
        val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                channelId,
                "Gravação de Tela",
                NotificationManager.IMPORTANCE_LOW
            )
            manager.createNotificationChannel(channel)
        }

        val notification: Notification = NotificationCompat.Builder(this, channelId)
            .setContentTitle("Gravação de Tela Ativa")
            .setContentText("Gravando o extrato para a Inteligência Artificial...")
            .setSmallIcon(android.R.drawable.ic_menu_camera)
            .setOngoing(true)
            .build()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            if (Build.VERSION.SDK_INT >= 34) { // Android 14+
                startForeground(
                    1009,
                    notification,
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION
                )
            } else {
                startForeground(
                    1009,
                    notification,
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION
                )
            }
        } else {
            startForeground(1009, notification)
        }
    }

    private fun startRecording(resultCode: Int, resultData: Intent) {
        try {
            val windowManager = getSystemService(Context.WINDOW_SERVICE) as WindowManager
            val metrics = DisplayMetrics()
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                val bounds = windowManager.currentWindowMetrics.bounds
                metrics.widthPixels = bounds.width()
                metrics.heightPixels = bounds.height()
                metrics.densityDpi = resources.displayMetrics.densityDpi
            } else {
                @Suppress("DEPRECATION")
                windowManager.defaultDisplay.getMetrics(metrics)
            }

            var width = metrics.widthPixels
            var height = metrics.heightPixels
            if (width % 2 != 0) width -= 1
            if (height % 2 != 0) height -= 1

            val outputFile = File(cacheDir, "extrato_gravado_${System.currentTimeMillis()}.mp4")
            currentOutputFile = outputFile

            mediaRecorder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                MediaRecorder(this)
            } else {
                @Suppress("DEPRECATION")
                MediaRecorder()
            }.apply {
                setVideoSource(MediaRecorder.VideoSource.SURFACE)
                setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
                setVideoEncoder(MediaRecorder.VideoEncoder.H264)
                setVideoSize(width, height)
                setVideoFrameRate(30)
                setVideoEncodingBitRate(3 * 1024 * 1024)
                setOutputFile(outputFile.absolutePath)
                prepare()
            }

            val projectionManager = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
            mediaProjection = projectionManager.getMediaProjection(resultCode, resultData)

            // REGISTRO OBRIGATÓRIO NO ANDROID 14 (API 34+) PARA EVITAR ILLEGAL STATE EXCEPTION
            if (Build.VERSION.SDK_INT >= 34) {
                mediaProjection?.registerCallback(object : MediaProjection.Callback() {
                    override fun onStop() {
                        stopRecordingInternal()
                    }
                }, Handler(Looper.getMainLooper()))
            }

            virtualDisplay = mediaProjection?.createVirtualDisplay(
                "NativeVideoRecorderDisplay",
                metrics.widthPixels,
                metrics.heightPixels,
                metrics.densityDpi,
                DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
                mediaRecorder?.surface,
                null,
                null
            )

            mediaRecorder?.start()
            isRecording = true
        } catch (e: Exception) {
            e.printStackTrace()
            stopRecordingInternal()
            stopSelf()
        }
    }

    private fun stopRecordingInternal() {
        if (!isRecording) return
        try {
            mediaRecorder?.stop()
            mediaRecorder?.reset()
            mediaRecorder?.release()
        } catch (e: Exception) {
            e.printStackTrace()
        }
        try {
            virtualDisplay?.release()
            mediaProjection?.stop()
        } catch (e: Exception) {
            e.printStackTrace()
        }
        virtualDisplay = null
        mediaRecorder = null
        mediaProjection = null
        isRecording = false
        lastOutputFile = currentOutputFile?.absolutePath
    }

    override fun onDestroy() {
        stopRecordingInternal()
        super.onDestroy()
    }
}

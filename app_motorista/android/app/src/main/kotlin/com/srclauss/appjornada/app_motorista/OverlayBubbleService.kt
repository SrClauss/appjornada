package com.srclauss.appjornada.app_motorista

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.PixelFormat
import android.graphics.drawable.GradientDrawable
import android.hardware.display.DisplayManager
import android.hardware.display.VirtualDisplay
import android.media.Image
import android.media.ImageReader
import android.media.projection.MediaProjection
import android.media.projection.MediaProjectionManager
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.util.DisplayMetrics
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.widget.ImageView
import androidx.core.app.NotificationCompat
import java.io.File
import java.io.FileOutputStream
import java.io.IOException

class OverlayBubbleService : Service() {

    private lateinit var windowManager: WindowManager
    private var floatingButton: ImageView? = null
    private var mediaProjection: MediaProjection? = null
    private var mediaProjectionManager: MediaProjectionManager? = null
    private var isCapturing = false

    companion object {
        const val ACTION_START = "ACTION_START"
        const val ACTION_STOP = "ACTION_STOP"
        const val EXTRA_RESULT_CODE = "EXTRA_RESULT_CODE"
        const val EXTRA_RESULT_DATA = "EXTRA_RESULT_DATA"
        const val ACTION_SCREENSHOT_CAPTURED = "com.srclauss.appjornada.SCREENSHOT_CAPTURED"
        const val EXTRA_FILE_PATH = "EXTRA_FILE_PATH"
        private const val NOTIFICATION_ID = 9999
        private const val CHANNEL_ID = "overlay_bubble_channel"
        @JvmStatic
        var isServiceRunning = false
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        isServiceRunning = true
        windowManager = getSystemService(Context.WINDOW_SERVICE) as WindowManager
        mediaProjectionManager = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent == null) {
            stopSelf()
            return START_NOT_STICKY
        }

        val action = intent.action
        if (action == ACTION_STOP) {
            stopSelf()
            return START_NOT_STICKY
        }

        val resultCode = intent.getIntExtra(EXTRA_RESULT_CODE, 0)
        val resultData = intent.getParcelableExtra<Intent>(EXTRA_RESULT_DATA)

        if (resultCode != 0 && resultData != null) {
            startForegroundServiceWithNotification()
            setupMediaProjection(resultCode, resultData)
            setupFloatingButton()
        } else {
            stopSelf()
        }

        return START_NOT_STICKY
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Serviço de Botão Suspenso",
                NotificationManager.IMPORTANCE_LOW
            )
            val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            manager.createNotificationChannel(channel)
        }
    }

    private fun startForegroundServiceWithNotification() {
        val notification: Notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Botão Suspenso Ativo")
            .setContentText("Toque na bolinha flutuante para tirar print das corridas.")
            .setSmallIcon(android.R.drawable.ic_menu_camera)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(
                NOTIFICATION_ID,
                notification,
                ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION
            )
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
    }

    private fun setupMediaProjection(resultCode: Int, resultData: Intent) {
        mediaProjection = mediaProjectionManager?.getMediaProjection(resultCode, resultData)
        mediaProjection?.registerCallback(object : MediaProjection.Callback() {
            override fun onStop() {
                mediaProjection = null
                stopSelf()
            }
        }, Handler(Looper.getMainLooper()))
    }

    private fun setupFloatingButton() {
        if (floatingButton != null) return

        val layoutParams = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
                WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
            else
                WindowManager.LayoutParams.TYPE_PHONE,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE,
            PixelFormat.TRANSLUCENT
        )

        layoutParams.gravity = Gravity.TOP or Gravity.START
        layoutParams.x = 100
        layoutParams.y = 500

        val button = ImageView(this)
        button.setImageResource(android.R.drawable.ic_menu_camera)
        button.setColorFilter(Color.WHITE)

        val sizePx = (56 * resources.displayMetrics.density).toInt()
        val paddingPx = (14 * resources.displayMetrics.density).toInt()
        button.layoutParams = WindowManager.LayoutParams(sizePx, sizePx)
        button.setPadding(paddingPx, paddingPx, paddingPx, paddingPx)

        val shape = GradientDrawable()
        shape.shape = GradientDrawable.OVAL
        shape.setColor(Color.parseColor("#6366F1")) // Indigo
        shape.setStroke(4, Color.WHITE)
        button.background = shape

        button.setOnTouchListener(object : View.OnTouchListener {
            private var lastAction: Int = 0
            private var initialX: Int = 0
            private var initialY: Int = 0
            private var initialTouchX: Float = 0f
            private var initialTouchY: Float = 0f

            override fun onTouch(v: View, event: MotionEvent): Boolean {
                when (event.action) {
                    MotionEvent.ACTION_DOWN -> {
                        initialX = layoutParams.x
                        initialY = layoutParams.y
                        initialTouchX = event.rawX
                        initialTouchY = event.rawY
                        lastAction = event.action
                        return true
                    }
                    MotionEvent.ACTION_UP -> {
                        if (lastAction == MotionEvent.ACTION_DOWN) {
                            // Clicou no botão
                            takeScreenshot()
                        }
                        lastAction = event.action
                        return true
                    }
                    MotionEvent.ACTION_MOVE -> {
                        layoutParams.x = initialX + (event.rawX - initialTouchX).toInt()
                        layoutParams.y = initialY + (event.rawY - initialTouchY).toInt()
                        windowManager.updateViewLayout(button, layoutParams)
                        if (Math.abs(event.rawX - initialTouchX) > 10 || Math.abs(event.rawY - initialTouchY) > 10) {
                            lastAction = MotionEvent.ACTION_MOVE
                        }
                        return true
                    }
                }
                return false
            }
        })

        floatingButton = button
        windowManager.addView(floatingButton, layoutParams)
    }

    private fun takeScreenshot() {
        if (isCapturing || mediaProjection == null) return
        isCapturing = true

        // Animação rápida de clique
        floatingButton?.alpha = 0.5f

        val metrics = DisplayMetrics()
        windowManager.defaultDisplay.getRealMetrics(metrics)
        val width = metrics.widthPixels
        val height = metrics.heightPixels
        val density = metrics.densityDpi

        val imageReader = ImageReader.newInstance(width, height, PixelFormat.RGBA_8888, 2)
        val virtualDisplay: VirtualDisplay? = mediaProjection!!.createVirtualDisplay(
            "ScreenCapture",
            width,
            height,
            density,
            DisplayManager.VIRTUAL_DISPLAY_FLAG_OWN_CONTENT_ONLY,
            imageReader.surface,
            null,
            null
        )

        val handler = Handler(Looper.getMainLooper())
        
        // Timeout para caso não receba frame
        val timeoutRunnable = Runnable {
            cleanupCapture(virtualDisplay, imageReader)
        }
        handler.postDelayed(timeoutRunnable, 3000)

        imageReader.setOnImageAvailableListener({ reader ->
            val image: Image? = reader.acquireLatestImage()
            if (image != null) {
                handler.removeCallbacks(timeoutRunnable)
                try {
                    val path = processImage(image, width, height)
                    if (path != null) {
                        broadcastScreenshotCaptured(path)
                    }
                } catch (e: Exception) {
                    e.printStackTrace()
                } finally {
                    image.close()
                    cleanupCapture(virtualDisplay, imageReader)
                }
            }
        }, handler)
    }

    private fun cleanupCapture(virtualDisplay: VirtualDisplay?, imageReader: ImageReader) {
        virtualDisplay?.release()
        imageReader.close()
        floatingButton?.alpha = 1.0f
        isCapturing = false
    }

    private fun processImage(image: Image, width: Int, height: Int): String? {
        val planes = image.planes
        val buffer = planes[0].buffer
        val pixelStride = planes[0].pixelStride
        val rowStride = planes[0].rowStride
        val rowPadding = rowStride - pixelStride * width

        val bitmap = Bitmap.createBitmap(
            width + rowPadding / pixelStride,
            height,
            Bitmap.Config.ARGB_8888
        )
        bitmap.copyPixelsFromBuffer(buffer)

        // Corta para remover qualquer padding lateral introduzido pelo buffer
        val croppedBitmap = Bitmap.createBitmap(bitmap, 0, 0, width, height)
        bitmap.recycle()

        // Salva na pasta de cache
        val cacheDir = externalCacheDir ?: cacheDir
        val file = File(cacheDir, "print_corrida_${System.currentTimeMillis()}.jpg")
        
        var fos: FileOutputStream? = null
        try {
            fos = FileOutputStream(file)
            croppedBitmap.compress(Bitmap.CompressFormat.JPEG, 90, fos)
            croppedBitmap.recycle()
            return file.absolutePath
        } catch (e: IOException) {
            e.printStackTrace()
        } finally {
            fos?.close()
        }
        return null
    }

    private fun broadcastScreenshotCaptured(filePath: String) {
        val intent = Intent(ACTION_SCREENSHOT_CAPTURED)
        intent.putExtra(EXTRA_FILE_PATH, filePath)
        sendBroadcast(intent)
    }

    override fun onDestroy() {
        if (floatingButton != null) {
            windowManager.removeView(floatingButton)
            floatingButton = null
        }
        mediaProjection?.stop()
        mediaProjection = null
        isServiceRunning = false
        super.onDestroy()
    }
}

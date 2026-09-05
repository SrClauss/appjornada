package com.srclauss.appjornada.app_motorista

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.graphics.Bitmap
import android.graphics.Canvas
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
import android.widget.LinearLayout
import androidx.core.app.NotificationCompat
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import android.location.LocationManager

class OverlayBubbleService : Service() {

    private lateinit var windowManager: WindowManager
    private var floatingContainer: LinearLayout? = null
    private var isMinimized = false
    private var isExpanded = false
    private val collapseHandler = Handler(Looper.getMainLooper())
    private val collapseRunnable = Runnable {
        isExpanded = false
        floatingContainer?.let { updateBarLayout(it) }
    }

    private fun resetCollapseTimer() {
        collapseHandler.removeCallbacks(collapseRunnable)
        if (isExpanded) {
            collapseHandler.postDelayed(collapseRunnable, 5000)
        }
    }

    private var warningActive = false
    private var isVideoMode = false
    private var isRecordingVideo = false
    private var savedResultCode: Int = 0
    private var savedResultData: Intent? = null
    private var warningType: String? = null
    private var warningFilePath: String? = null
    private var warningPlataforma: String? = null
    private var warningValor = 0.0
    private var warningOrigem: String? = null
    private var warningDestino: String? = null
    private var mediaProjection: MediaProjection? = null
    private var mediaProjectionManager: MediaProjectionManager? = null
    private var isCapturing = false

    private var isRideActive = false
    private var rideStartTime = 0L
    private var rideStartLat = 0.0
    private var rideStartLon = 0.0
    private val rideRoutePoints = ArrayList<Pair<Double, Double>>()
    private var locationManager: LocationManager? = null
    private val locationListener = object : android.location.LocationListener {
        override fun onLocationChanged(location: android.location.Location) {
            if (isRideActive) {
                rideRoutePoints.add(Pair(location.latitude, location.longitude))
            }
        }
        override fun onStatusChanged(provider: String?, status: Int, extras: android.os.Bundle?) {}
        override fun onProviderEnabled(provider: String) {}
        override fun onProviderDisabled(provider: String) {}
    }

    private var capWasRideActive = false
    private var capStartLat = 0.0
    private var capStartLon = 0.0
    private var capEndLat = 0.0
    private var capEndLon = 0.0
    private var capStartTime = 0L
    private var capEndTime = 0L
    private val capRoutePoints = ArrayList<Pair<Double, Double>>()

    private fun startRideTracking() {
        rideRoutePoints.clear()
        rideStartTime = System.currentTimeMillis()
        try {
            locationManager = getSystemService(Context.LOCATION_SERVICE) as LocationManager
            locationManager?.requestLocationUpdates(
                LocationManager.GPS_PROVIDER,
                2000L,
                2f,
                locationListener
            )
            val lastKnown = locationManager?.getLastKnownLocation(LocationManager.GPS_PROVIDER)
                ?: locationManager?.getLastKnownLocation(LocationManager.NETWORK_PROVIDER)
            lastKnown?.let {
                rideStartLat = it.latitude
                rideStartLon = it.longitude
                rideRoutePoints.add(Pair(it.latitude, it.longitude))
            }
        } catch (e: SecurityException) {
            e.printStackTrace()
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    private fun stopRideTracking() {
        try {
            locationManager?.removeUpdates(locationListener)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

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

        if (action == "ACTION_SET_VISIBLE") {
            val visible = intent.getBooleanExtra("visible", true)
            floatingContainer?.visibility = if (visible) View.VISIBLE else View.GONE
            return START_NOT_STICKY
        }

        if (action == "ACTION_SET_WARNING") {
            warningActive = intent.getBooleanExtra("warning_active", false)
            warningType = intent.getStringExtra("warning_type") ?: "REVISAO"
            warningFilePath = intent.getStringExtra("filePath")
            warningPlataforma = intent.getStringExtra("plataforma")
            warningValor = intent.getDoubleExtra("valor", 0.0)
            warningOrigem = intent.getStringExtra("origem")
            warningDestino = intent.getStringExtra("destino")
            
            floatingContainer?.let { updateBarLayout(it) }
            return START_NOT_STICKY
        }

        startForegroundServiceWithNotification()
        setupFloatingButton()

        val resultCode = intent.getIntExtra(EXTRA_RESULT_CODE, 0)
        val resultData = intent.getParcelableExtra<Intent>(EXTRA_RESULT_DATA)
        
        isVideoMode = intent.getBooleanExtra("EXTRA_VIDEO_MODE", false)
        if (resultCode != 0) {
            savedResultCode = resultCode
        }
        if (resultData != null) {
            savedResultData = resultData
        }

        if (resultCode != 0 && resultData != null) {
            setupMediaProjection(resultCode, resultData)
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
        if (floatingContainer != null) return

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

        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            val padding = (8 * resources.displayMetrics.density).toInt()
            setPadding(padding, padding, padding, padding)
            alpha = 0.6f
        }

        val shape = GradientDrawable().apply {
            shape = GradientDrawable.RECTANGLE
            cornerRadius = 28 * resources.displayMetrics.density
            setColor(Color.parseColor("#1E293B")) // Slate 800
            setStroke(4, Color.WHITE)
        }
        container.background = shape

        updateBarLayout(container)

        floatingContainer = container
        windowManager.addView(container, layoutParams)
    }

    private fun updateBarLayout(container: LinearLayout) {
        container.removeAllViews()

        val density = resources.displayMetrics.density
        val btnSize = (40 * density).toInt()
        val padding = (8 * density).toInt()

        val windowParams = container.layoutParams as? WindowManager.LayoutParams

        // A Alça (Handle)
        val handle = ImageView(this).apply {
            setImageResource(android.R.drawable.ic_menu_sort_by_size)
            if (warningActive) {
                setColorFilter(Color.parseColor("#EF4444")) // Vermelho se houver aviso
            } else {
                setColorFilter(Color.parseColor("#94A3B8")) // Slate Gray
            }
            layoutParams = LinearLayout.LayoutParams((32 * density).toInt(), (24 * density).toInt()).apply {
                topMargin = (4 * density).toInt()
                bottomMargin = if (isExpanded) (8 * density).toInt() else (4 * density).toInt()
            }
            setPadding(0, (4 * density).toInt(), 0, (4 * density).toInt())
            setOnClickListener {
                isExpanded = !isExpanded
                updateBarLayout(container)
                resetCollapseTimer()
            }

            setOnTouchListener(object : View.OnTouchListener {
                private var lastAction: Int = 0
                private var initialX: Int = 0
                private var initialY: Int = 0
                private var initialTouchX: Float = 0f
                private var initialTouchY: Float = 0f

                override fun onTouch(v: View, event: MotionEvent): Boolean {
                    resetCollapseTimer()
                    if (windowParams == null) return false
                    when (event.action) {
                        MotionEvent.ACTION_DOWN -> {
                            container.alpha = 1.0f
                            initialX = windowParams.x
                            initialY = windowParams.y
                            initialTouchX = event.rawX
                            initialTouchY = event.rawY
                            lastAction = event.action
                            return true
                        }
                        MotionEvent.ACTION_UP -> {
                            container.alpha = if (isExpanded) 1.0f else 0.6f
                            if (lastAction == MotionEvent.ACTION_DOWN) {
                                performClick()
                            }
                            lastAction = event.action
                            return true
                        }
                        MotionEvent.ACTION_MOVE -> {
                            windowParams.x = initialX + (event.rawX - initialTouchX).toInt()
                            windowParams.y = initialY + (event.rawY - initialTouchY).toInt()
                            windowManager.updateViewLayout(container, windowParams)
                            if (Math.abs(event.rawX - initialTouchX) > 10 || Math.abs(event.rawY - initialTouchY) > 10) {
                                lastAction = MotionEvent.ACTION_MOVE
                            }
                            return true
                        }
                        MotionEvent.ACTION_CANCEL -> {
                            container.alpha = if (isExpanded) 1.0f else 0.6f
                            return true
                        }
                    }
                    return false
                }
            })
        }

        container.addView(handle)

        if (isExpanded) {
            container.alpha = 1.0f
            
                        if (isVideoMode) {
                // Botão GRAVAR/PARAR VÍDEO
                val videoBtn = ImageView(this).apply {
                    if (isRecordingVideo) {
                        setImageResource(android.R.drawable.ic_media_pause)
                        setColorFilter(Color.parseColor("#EF4444")) // Red STOP
                    } else {
                        setImageResource(android.R.drawable.ic_media_play)
                        setColorFilter(Color.parseColor("#10B981")) // Green START
                    }
                    layoutParams = LinearLayout.LayoutParams(btnSize, btnSize).apply {
                        bottomMargin = (8 * density).toInt()
                    }
                    setPadding(padding, padding, padding, padding)
                    setOnClickListener {
                        resetCollapseTimer()
                        if (isRecordingVideo) {
                            // STOP
                            val serviceIntent = Intent(this@OverlayBubbleService, NativeVideoRecorderService::class.java).apply {
                                action = NativeVideoRecorderService.ACTION_STOP
                            }
                            startService(serviceIntent)
                            android.widget.Toast.makeText(this@OverlayBubbleService, "⏹️ Gravação finalizada! Retornando ao app...", android.widget.Toast.LENGTH_LONG).show()
                            
                            val intent = packageManager.getLaunchIntentForPackage(packageName)?.apply {
                                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
                            }
                            if (intent != null) {
                                startActivity(intent)
                            }
                            stopSelf()
                        } else {
                            // START
                            val serviceIntent = Intent(this@OverlayBubbleService, NativeVideoRecorderService::class.java).apply {
                                action = NativeVideoRecorderService.ACTION_START
                                putExtra(NativeVideoRecorderService.EXTRA_RESULT_CODE, savedResultCode)
                                putExtra(NativeVideoRecorderService.EXTRA_RESULT_DATA, savedResultData)
                            }
                            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                                startForegroundService(serviceIntent)
                            } else {
                                startService(serviceIntent)
                            }
                            isRecordingVideo = true
                            updateBarLayout(container)
                            android.widget.Toast.makeText(this@OverlayBubbleService, "▶️ Gravação de tela iniciada!", android.widget.Toast.LENGTH_SHORT).show()
                        }
                    }
                }
                container.addView(videoBtn)
            } else {
                // Screenshot buttons (only when NOT in video mode)
                val screenshotBtn = ImageView(this).apply {
                    setImageResource(android.R.drawable.ic_menu_camera)
                    setColorFilter(Color.parseColor("#38BDF8"))
                    layoutParams = LinearLayout.LayoutParams(btnSize, btnSize).apply {
                        bottomMargin = (8 * density).toInt()
                    }
                    setPadding(padding, padding, padding, padding)
                    setOnClickListener {
                        resetCollapseTimer()
                        takeScreenshot()
                    }
                }
                container.addView(screenshotBtn)
            }
        } else {
            container.alpha = 0.6f
        }
    }

    private fun isBitmapTransparent(bitmap: Bitmap): Boolean {
        val w = bitmap.width
        val h = bitmap.height
        val stepX = (w / 20).coerceAtLeast(1)
        val stepY = (h / 20).coerceAtLeast(1)
        for (y in 0 until h step stepY) {
            for (x in 0 until w step stepX) {
                val pixel = bitmap.getPixel(x, y)
                if (Color.alpha(pixel) > 0) {
                    return false
                }
            }
        }
        return true
    }

    private fun takeScreenshot() {
        if (isCapturing || mediaProjection == null) return
        isCapturing = true

        val wasRideActive = isRideActive
        val sLat = rideStartLat
        val sLon = rideStartLon
        val sTime = rideStartTime
        val routeCopy = ArrayList(rideRoutePoints)

        if (isRideActive) {
            stopRideTracking()
            isRideActive = false
            floatingContainer?.let { updateBarLayout(it) }
        }

        var eLat = sLat
        var eLon = sLon
        val eTime = System.currentTimeMillis()

        if (wasRideActive) {
            try {
                val lastKnown = locationManager?.getLastKnownLocation(LocationManager.GPS_PROVIDER)
                    ?: locationManager?.getLastKnownLocation(LocationManager.NETWORK_PROVIDER)
                lastKnown?.let {
                    eLat = it.latitude
                    eLon = it.longitude
                    routeCopy.add(Pair(it.latitude, it.longitude))
                }
            } catch (e: SecurityException) {
                e.printStackTrace()
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }

        capWasRideActive = wasRideActive
        capStartLat = sLat
        capStartLon = sLon
        capEndLat = eLat
        capEndLon = eLon
        capStartTime = sTime
        capEndTime = eTime
        capRoutePoints.clear()
        capRoutePoints.addAll(routeCopy)

        // Esconde o menu flutuante temporariamente para não aparecer na captura de tela
        floatingContainer?.visibility = View.GONE

        val metrics = DisplayMetrics()
        windowManager.defaultDisplay.getRealMetrics(metrics)
        val width = metrics.widthPixels
        val height = metrics.heightPixels
        val density = metrics.densityDpi

        // Pequeno delay para garantir que a janela flutuante sumiu da renderização antes do print
        Handler(Looper.getMainLooper()).postDelayed({
            val imageReader = ImageReader.newInstance(width, height, PixelFormat.RGBA_8888, 2)
            val virtualDisplay: VirtualDisplay? = mediaProjection!!.createVirtualDisplay(
                "ScreenCapture",
                width,
                height,
                density,
                DisplayManager.VIRTUAL_DISPLAY_FLAG_AUTO_MIRROR,
                imageReader.surface,
                null,
                null
            )

            val handler = Handler(Looper.getMainLooper())
            
            // Timeout para caso não receba frame válido
            val timeoutRunnable = Runnable {
                cleanupCapture(virtualDisplay, imageReader)
            }
            handler.postDelayed(timeoutRunnable, 3000)

            imageReader.setOnImageAvailableListener({ reader ->
                val image: Image? = reader.acquireLatestImage()
                if (image != null) {
                    try {
                        val path = processImage(image, width, height)
                        if (path != null) {
                            handler.removeCallbacks(timeoutRunnable)
                            broadcastScreenshotCaptured(
                                path,
                                capWasRideActive,
                                capStartLat,
                                capStartLon,
                                capEndLat,
                                capEndLon,
                                capStartTime,
                                capEndTime,
                                capRoutePoints
                            )
                            image.close()
                            cleanupCapture(virtualDisplay, imageReader)
                        } else {
                            // Frame em branco/transparente, descarta e espera o próximo válido
                            image.close()
                        }
                    } catch (e: Exception) {
                        e.printStackTrace()
                        try { image.close() } catch (ex: Exception) {}
                        cleanupCapture(virtualDisplay, imageReader)
                    }
                }
            }, handler)
        }, 150)
    }

    private fun cleanupCapture(virtualDisplay: VirtualDisplay?, imageReader: ImageReader) {
        virtualDisplay?.release()
        imageReader.close()
        
        // Restaura a visibilidade da bolinha flutuante
        floatingContainer?.visibility = View.VISIBLE
        floatingContainer?.alpha = if (isExpanded) 1.0f else 0.6f
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

        // Se o frame capturado for 100% transparente/vazio, descarta-o
        if (isBitmapTransparent(croppedBitmap)) {
            croppedBitmap.recycle()
            return null
        }

        // Cria um bitmap opaco com fundo branco para evitar que pixels transparentes/semi-transparentes fiquem pretos/escuros ao salvar em JPEG
        val opaqueBitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(opaqueBitmap)
        canvas.drawColor(Color.WHITE)
        canvas.drawBitmap(croppedBitmap, 0f, 0f, null)
        croppedBitmap.recycle()

        // Salva na pasta de cache
        val cacheDir = externalCacheDir ?: cacheDir
        val file = File(cacheDir, "print_corrida_${System.currentTimeMillis()}.jpg")
        
        var fos: FileOutputStream? = null
        try {
            fos = FileOutputStream(file)
            opaqueBitmap.compress(Bitmap.CompressFormat.JPEG, 90, fos)
            opaqueBitmap.recycle()
            return file.absolutePath
        } catch (e: IOException) {
            e.printStackTrace()
        } finally {
            fos?.close()
        }
        return null
    }

    private fun broadcastScreenshotCaptured(
        filePath: String,
        isRideRecord: Boolean,
        startLat: Double,
        startLon: Double,
        endLat: Double,
        endLon: Double,
        startTime: Long,
        endTime: Long,
        routePoints: ArrayList<Pair<Double, Double>>
    ) {
        val intent = Intent(ACTION_SCREENSHOT_CAPTURED)
        intent.putExtra(EXTRA_FILE_PATH, filePath)
        intent.putExtra("is_ride_record", isRideRecord)
        intent.putExtra("start_lat", startLat)
        intent.putExtra("start_lon", startLon)
        intent.putExtra("end_lat", endLat)
        intent.putExtra("end_lon", endLon)
        intent.putExtra("start_time", startTime)
        intent.putExtra("end_time", endTime)
        
        val routeArray = DoubleArray(routePoints.size * 2)
        for (i in routePoints.indices) {
            routeArray[i * 2] = routePoints[i].first
            routeArray[i * 2 + 1] = routePoints[i].second
        }
        intent.putExtra("route_points", routeArray)
        sendBroadcast(intent)
    }

    override fun onDestroy() {
        if (floatingContainer != null) {
            windowManager.removeView(floatingContainer)
            floatingContainer = null
        }
        mediaProjection?.stop()
        mediaProjection = null
        isServiceRunning = false
        super.onDestroy()
    }
}

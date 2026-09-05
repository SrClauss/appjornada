import re
import os

main_activity_path = "app_motorista/android/app/src/main/kotlin/com/srclauss/appjornada/app_motorista/MainActivity.kt"
with open(main_activity_path, "r") as f:
    main_activity_content = f.read()

# Replace the block for REQUEST_VIDEO_RECORD_CAPTURE in MainActivity
old_block = """        if (requestCode == REQUEST_VIDEO_RECORD_CAPTURE) {
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
        }"""

new_block = """        if (requestCode == REQUEST_VIDEO_RECORD_CAPTURE) {
            if (resultCode == Activity.RESULT_OK && data != null) {
                val serviceIntent = Intent(this, OverlayBubbleService::class.java).apply {
                    action = OverlayBubbleService.ACTION_START
                    putExtra(OverlayBubbleService.EXTRA_RESULT_CODE, resultCode)
                    putExtra(OverlayBubbleService.EXTRA_RESULT_DATA, data)
                    putExtra("EXTRA_VIDEO_MODE", true)
                }
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    startForegroundService(serviceIntent)
                } else {
                    startService(serviceIntent)
                }
                moveTaskToBack(true)
                methodChannelResult?.success(true)
            } else {
                methodChannelResult?.error("CAPTURE_DENIED", "Permissão de gravação de tela negada", null)
            }
            methodChannelResult = null
        }"""

main_activity_content = main_activity_content.replace(old_block, new_block)

with open(main_activity_path, "w") as f:
    f.write(main_activity_content)

print("MainActivity patched.")

overlay_service_path = "app_motorista/android/app/src/main/kotlin/com/srclauss/appjornada/app_motorista/OverlayBubbleService.kt"
with open(overlay_service_path, "r") as f:
    overlay_content = f.read()

# Add isVideoMode and isRecordingVideo vars
overlay_content = overlay_content.replace(
    "private var warningActive = false",
    "private var warningActive = false\n    private var isVideoMode = false\n    private var isRecordingVideo = false"
)

# Read EXTRA_VIDEO_MODE
overlay_content = overlay_content.replace(
    "intent.getParcelableExtra(EXTRA_RESULT_DATA)",
    "intent.getParcelableExtra(EXTRA_RESULT_DATA)\n                isVideoMode = intent.getBooleanExtra(\"EXTRA_VIDEO_MODE\", false)"
)

# Update layout to show Start/Stop Video buttons
old_layout_block = """            // Botão 🔴 PARAR GRAVAÇÃO DE TELA
            val videoBtn = ImageView(this).apply {
                setImageResource(android.R.drawable.ic_media_pause)
                setColorFilter(Color.parseColor("#EF4444")) // Bright Red STOP
                layoutParams = LinearLayout.LayoutParams(btnSize, btnSize).apply {
                    bottomMargin = (8 * density).toInt()
                }
                setPadding(padding, padding, padding, padding)
                setOnClickListener {
                    resetCollapseTimer()
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
                }
            }

            container.addView(videoBtn)"""

new_layout_block = """            if (isVideoMode) {
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
                                putExtra(NativeVideoRecorderService.EXTRA_RESULT_CODE, resultCode)
                                putExtra(NativeVideoRecorderService.EXTRA_RESULT_DATA, resultData)
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
            }"""

# We need to find the old_layout_block and replace it. Wait, the old code might have more screenshot buttons.
# Let's just do a regex replace to replace from "// Botão 🔴 PARAR GRAVAÇÃO DE TELA" to the end of the if (isExpanded) block.
import re
overlay_content = re.sub(
    r"// Botão 🔴 PARAR GRAVAÇÃO DE TELA.*?(?=        \} else \{)", 
    new_layout_block + "\n", 
    overlay_content, 
    flags=re.DOTALL
)

with open(overlay_service_path, "w") as f:
    f.write(overlay_content)

print("OverlayBubbleService patched.")


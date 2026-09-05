import re

file_path = "app_motorista/android/app/src/main/kotlin/com/srclauss/appjornada/app_motorista/MainActivity.kt"
with open(file_path, "r") as f:
    content = f.read()

# Add checkAndRequestVideoOverlayPermission
new_function = """    private fun checkAndRequestVideoOverlayPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && !Settings.canDrawOverlays(this)) {
            val intent = Intent(
                Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                Uri.parse("package:$packageName")
            )
            // Request permission, but when it returns we want it to go to video capture.
            startActivityForResult(intent, 1004) // REQUEST_VIDEO_OVERLAY_PERMISSION
        } else {
            requestVideoScreenCapture()
        }
    }

    private fun requestVideoScreenCapture() {
        val mediaProjectionManager = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
        val intent = if (Build.VERSION.SDK_INT >= 34) {
            val config = MediaProjectionConfig.createConfigForUserChoice()
            mediaProjectionManager.createScreenCaptureIntent(config)
        } else {
            mediaProjectionManager.createScreenCaptureIntent()
        }
        startActivityForResult(intent, REQUEST_VIDEO_RECORD_CAPTURE)
    }
"""

content = content.replace("    private fun checkAndRequestOverlayPermission() {", new_function + "\n    private fun checkAndRequestOverlayPermission() {")

# Update startNativeVideoRecorder
old_start = """                "startNativeVideoRecorder" -> {
                    methodChannelResult = result
                    val mediaProjectionManager = getSystemService(Context.MEDIA_PROJECTION_SERVICE) as MediaProjectionManager
                    val intent = if (Build.VERSION.SDK_INT >= 34) {
                        val config = MediaProjectionConfig.createConfigForUserChoice()
                        mediaProjectionManager.createScreenCaptureIntent(config)
                    } else {
                        mediaProjectionManager.createScreenCaptureIntent()
                    }
                    startActivityForResult(intent, REQUEST_VIDEO_RECORD_CAPTURE)
                }"""

new_start = """                "startNativeVideoRecorder" -> {
                    methodChannelResult = result
                    checkAndRequestVideoOverlayPermission()
                }"""
content = content.replace(old_start, new_start)

# Add handling for 1004
old_on_activity_result = """        if (requestCode == REQUEST_OVERLAY_PERMISSION) {"""
new_on_activity_result = """        if (requestCode == 1004) { // REQUEST_VIDEO_OVERLAY_PERMISSION
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && Settings.canDrawOverlays(this)) {
                requestVideoScreenCapture()
            } else {
                methodChannelResult?.error("PERMISSION_DENIED", "Overlay permission not granted", null)
                methodChannelResult = null
            }
        }

        if (requestCode == REQUEST_OVERLAY_PERMISSION) {"""
content = content.replace(old_on_activity_result, new_on_activity_result)

with open(file_path, "w") as f:
    f.write(content)
print("Patched MainActivity.kt")


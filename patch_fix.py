import re

overlay_service_path = "app_motorista/android/app/src/main/kotlin/com/srclauss/appjornada/app_motorista/OverlayBubbleService.kt"
with open(overlay_service_path, "r") as f:
    content = f.read()

# I need to save resultCode and resultData in the service when they arrive.
content = content.replace(
    "private var isRecordingVideo = false",
    "private var isRecordingVideo = false\n    private var savedResultCode: Int = 0\n    private var savedResultData: Intent? = null"
)

# Find onStartCommand where they are read:
content = content.replace(
    "                isVideoMode = intent.getBooleanExtra(\"EXTRA_VIDEO_MODE\", false)",
    "                isVideoMode = intent.getBooleanExtra(\"EXTRA_VIDEO_MODE\", false)\n                savedResultCode = intent.getIntExtra(EXTRA_RESULT_CODE, 0)\n                savedResultData = intent.getParcelableExtra(EXTRA_RESULT_DATA)"
)

# And fix the references in the START button block
content = content.replace(
    "putExtra(NativeVideoRecorderService.EXTRA_RESULT_CODE, resultCode)",
    "putExtra(NativeVideoRecorderService.EXTRA_RESULT_CODE, savedResultCode)"
)
content = content.replace(
    "putExtra(NativeVideoRecorderService.EXTRA_RESULT_DATA, resultData)",
    "putExtra(NativeVideoRecorderService.EXTRA_RESULT_DATA, savedResultData)"
)

with open(overlay_service_path, "w") as f:
    f.write(content)

print("Fixed OverlayBubbleService.")

import re

overlay_service_path = "app_motorista/android/app/src/main/kotlin/com/srclauss/appjornada/app_motorista/OverlayBubbleService.kt"
with open(overlay_service_path, "r") as f:
    content = f.read()

# We need to find the lines:
#         val resultCode = intent.getIntExtra(EXTRA_RESULT_CODE, 0)
#         val resultData = intent.getParcelableExtra<Intent>(EXTRA_RESULT_DATA)
# and insert our state updates right after them.

old_lines = """        val resultCode = intent.getIntExtra(EXTRA_RESULT_CODE, 0)
        val resultData = intent.getParcelableExtra<Intent>(EXTRA_RESULT_DATA)"""

new_lines = """        val resultCode = intent.getIntExtra(EXTRA_RESULT_CODE, 0)
        val resultData = intent.getParcelableExtra<Intent>(EXTRA_RESULT_DATA)
        
        isVideoMode = intent.getBooleanExtra("EXTRA_VIDEO_MODE", false)
        if (resultCode != 0) {
            savedResultCode = resultCode
        }
        if (resultData != null) {
            savedResultData = resultData
        }"""

if old_lines in content:
    content = content.replace(old_lines, new_lines)
    with open(overlay_service_path, "w") as f:
        f.write(content)
    print("Fixed intent parsing!")
else:
    print("Could not find old lines!")


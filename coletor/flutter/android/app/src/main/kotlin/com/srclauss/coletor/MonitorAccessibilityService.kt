package com.srclauss.coletor

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.AccessibilityServiceInfo
import android.os.Build
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject

class MonitorAccessibilityService : AccessibilityService() {
    private val eventStore: EventStore by lazy { EventStore(applicationContext) }
    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private var debounceJob: Job? = null

    override fun onServiceConnected() {
        super.onServiceConnected()
        serviceInfo = (serviceInfo ?: AccessibilityServiceInfo()).apply {
            eventTypes =
                AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED or
                AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED
            packageNames = TARGET_PACKAGES.toTypedArray()
            feedbackType = AccessibilityServiceInfo.FEEDBACK_GENERIC
            notificationTimeout = NOTIFICATION_TIMEOUT_MS
            flags =
                AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS or
                AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS
        }
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        val safeEvent = event ?: return
        if (safeEvent.eventType != AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED &&
            safeEvent.eventType != AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED
        ) {
            return
        }

        val packageName = safeEvent.packageName?.toString() ?: return
        if (!TARGET_PACKAGES.contains(packageName)) return

        val activityClass = safeEvent.className?.toString().orEmpty()

        debounceJob?.cancel()
        debounceJob = serviceScope.launch {
            delay(DEBOUNCE_MS)

            val rootNode = rootInActiveWindow ?: return@launch
            val rootSnapshot = AccessibilityNodeInfo.obtain(rootNode)
            rootNode.recycle()

            withContext(Dispatchers.IO) {
                try {
                    val viewHierarchy = dumpViewHierarchy(rootSnapshot)
                    if (viewHierarchy.length() == 0) return@withContext

                    val payload = JSONObject()
                        .put("timestamp", System.currentTimeMillis())
                        .put("packageName", packageName)
                        .put("activityClass", activityClass)
                        .put("deviceModel", "${Build.MANUFACTURER} ${Build.MODEL}".trim())
                        .put("viewHierarchy", viewHierarchy)

                    eventStore.append(payload)
                } catch (_: Exception) {
                    Unit
                } finally {
                    rootSnapshot.recycle()
                }
            }
        }
    }

    override fun onInterrupt() = Unit

    override fun onDestroy() {
        debounceJob?.cancel()
        serviceScope.cancel()
        super.onDestroy()
    }

    private fun dumpViewHierarchy(node: AccessibilityNodeInfo): JSONArray {
        val nodes = JSONArray()
        collectVisibleNodes(node, nodes)
        return nodes
    }

    private fun collectVisibleNodes(node: AccessibilityNodeInfo, output: JSONArray) {
        if (!node.isVisibleToUser) return

        val className = node.className?.toString().orEmpty()
        val text = node.text?.toString()?.trim().orEmpty()
        val viewIdResourceName = node.viewIdResourceName?.trim().orEmpty()

        if (className.isNotEmpty() || text.isNotEmpty() || viewIdResourceName.isNotEmpty()) {
            output.put(
                JSONObject()
                    .put("className", className)
                    .put("text", text)
                    .put("viewIdResourceName", viewIdResourceName)
            )
        }

        val childCount = node.childCount
        for (index in 0 until childCount) {
            val child = try {
                node.getChild(index)
            } catch (_: Exception) {
                null
            } ?: continue

            try {
                collectVisibleNodes(child, output)
            } catch (_: Exception) {
                Unit
            } finally {
                child.recycle()
            }
        }
    }

    companion object {
        private const val DEBOUNCE_MS = 500L
        private const val NOTIFICATION_TIMEOUT_MS = 200L
        val TARGET_PACKAGES: Set<String> = setOf(
            "com.app99.driver",
            "com.ubercab.driver",
        )
    }
}

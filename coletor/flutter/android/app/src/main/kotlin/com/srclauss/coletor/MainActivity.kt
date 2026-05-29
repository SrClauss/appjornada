package com.srclauss.coletor

import android.accessibilityservice.AccessibilityServiceInfo
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.os.Build
import android.provider.Settings
import android.view.accessibility.AccessibilityManager
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import org.json.JSONArray

class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        val eventStore = EventStore(applicationContext)

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL)
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "status" -> {
                        result.success(
                            mapOf(
                                "accessibilityEnabled" to isAccessibilityEnabled(),
                                "eventCount" to eventStore.loadAll().length(),
                            )
                        )
                    }

                    "openAccessibilitySettings" -> {
                        val intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS).apply {
                            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                        }
                        startActivity(intent)
                        result.success(null)
                    }

                    "eventsForUpload" -> result.success(jsonArrayToMapList(eventStore.loadAll()))

                    "clearEvents" -> {
                        eventStore.clear()
                        result.success(null)
                    }

                    "markEventsAsSent" -> {
                        eventStore.clear()
                        result.success(null)
                    }

                    "deviceLabel" -> {
                        val label = "${Build.MANUFACTURER} ${Build.MODEL}".trim()
                        result.success(label)
                    }

                    else -> result.notImplemented()
                }
            }
    }

    private fun isAccessibilityEnabled(): Boolean {
        val manager = getSystemService(Context.ACCESSIBILITY_SERVICE) as AccessibilityManager
        val services = manager.getEnabledAccessibilityServiceList(AccessibilityServiceInfo.FEEDBACK_ALL_MASK)
        val target = ComponentName(this, MonitorAccessibilityService::class.java).flattenToShortString()
        return services.any { it.resolveInfo.serviceInfo.packageName == packageName && it.resolveInfo.serviceInfo.name.endsWith("MonitorAccessibilityService") } ||
            (Settings.Secure.getString(contentResolver, Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES)
                ?.contains(target) == true)
    }

    private fun jsonArrayToMapList(array: JSONArray): List<Map<String, Any?>> {
        val list = mutableListOf<Map<String, Any?>>()
        for (i in 0 until array.length()) {
            val obj = array.getJSONObject(i)
            val map = mutableMapOf<String, Any?>()
            obj.keys().forEach { key -> map[key] = obj.opt(key) }
            list.add(map)
        }
        return list
    }

    companion object {
        private const val CHANNEL = "appjornada/coletor_monitor"
    }
}

package com.srclauss.coletor

import android.content.Context
import android.os.Build
import org.json.JSONArray
import org.json.JSONObject

class EventStore(context: Context) {
    private val prefs = context.getSharedPreferences("coletor_events", Context.MODE_PRIVATE)

    fun append(packageName: String, activityClass: String?) {
        append(
            JSONObject()
                .put("timestamp", System.currentTimeMillis())
                .put("packageName", packageName)
                .put("activityClass", activityClass ?: "")
                .put("deviceModel", "${Build.MANUFACTURER} ${Build.MODEL}")
        )
    }

    fun append(entry: JSONObject) {
        val events = loadAll()
        events.put(entry)

        val trimmed = JSONArray()
        val start = if (events.length() > MAX_EVENTS) events.length() - MAX_EVENTS else 0
        for (i in start until events.length()) {
            trimmed.put(events.getJSONObject(i))
        }

        prefs.edit().putString(KEY_EVENTS, trimmed.toString()).apply()
    }

    fun appendViewHierarchy(
        packageName: String,
        activityClass: String?,
        viewHierarchy: JSONArray
    ) {
        val entry = JSONObject()
            .put("timestamp", System.currentTimeMillis())
            .put("packageName", packageName)
            .put("activityClass", activityClass ?: "")
            .put("deviceModel", "${Build.MANUFACTURER} ${Build.MODEL}")
            .put("viewHierarchy", viewHierarchy)
        if (viewHierarchy.length() > 0) {
            append(entry)
        }
    }

    fun loadAll(): JSONArray {
        val raw = prefs.getString(KEY_EVENTS, "[]") ?: "[]"
        return try {
            JSONArray(raw)
        } catch (_: Exception) {
            JSONArray()
        }
    }

    fun clear() {
        prefs.edit().putString(KEY_EVENTS, "[]").apply()
    }

    companion object {
        private const val KEY_EVENTS = "events_json"
        private const val MAX_EVENTS = 20000
    }
}

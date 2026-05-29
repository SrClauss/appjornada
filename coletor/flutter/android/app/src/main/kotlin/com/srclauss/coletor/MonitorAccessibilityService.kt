package com.srclauss.coletor

import android.accessibilityservice.AccessibilityService
import android.view.accessibility.AccessibilityEvent

class MonitorAccessibilityService : AccessibilityService() {
    private lateinit var eventStore: EventStore

    override fun onServiceConnected() {
        super.onServiceConnected()
        eventStore = EventStore(applicationContext)
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        val packageName = event?.packageName?.toString() ?: return
        if (!TARGET_PACKAGES.contains(packageName)) return

        val activityClass = event.className?.toString()
        eventStore.append(packageName, activityClass)
    }

    override fun onInterrupt() = Unit

    companion object {
        val TARGET_PACKAGES: Set<String> = setOf(
            "com.app99.driver",
            "com.ubercab.driver",
            "com.github.android",
        )
    }
}

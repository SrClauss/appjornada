package com.example.coletor_app

import android.accessibilityservice.AccessibilityService
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo

class MyAccessibilityService : AccessibilityService() {

    private val TAG = "ColetorAccessibility"

    // Guardas para evitar spam redundante se a árvore e o pacote não mudarem
    private var lastPackage: String = ""
    private var lastTreeHash: Int = 0

    override fun onServiceConnected() {
        super.onServiceConnected()
        Log.d(TAG, "Serviço de Acessibilidade estruturado conectado!")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event == null) return

        val packageName = event.packageName?.toString() ?: ""
        val className = event.className?.toString() ?: ""
        val eventType = AccessibilityEvent.eventTypeToString(event.eventType)

        var rootNode: AccessibilityNodeInfo? = null
        var serializedTree: Map<String, Any?>? = null

        try {
            rootNode = rootInActiveWindow
            if (rootNode != null) {
                serializedTree = serializeNodeSecurely(rootNode)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Falha de IPC ao obter raiz da tela", e)
        } finally {
            try {
                rootNode?.recycle()
            } catch (e: Exception) {
                // Silencia falhas
            }
        }

        // Se a árvore vier nula (tela vazia ou indisponível), não há o que reportar
        if (serializedTree == null) return

        // Calculamos um hash simples da árvore serializada para verificar alterações estruturais/textuais.
        // O toString() dos Maps aninhados do Kotlin gera uma string de conteúdo único representando toda a estrutura.
        val currentTreeHash = serializedTree.toString().hashCode()

        // Se o pacote e a estrutura textual/visual da tela forem idênticos, ignoramos o evento
        if (packageName == lastPackage && currentTreeHash == lastTreeHash) {
            return
        }

        lastPackage = packageName
        lastTreeHash = currentTreeHash

        Log.d(TAG, "Nova estrutura de tela capturada no app: $packageName")

        val payload = mapOf(
            "packageName" to packageName,
            "className" to className,
            "eventType" to eventType,
            "tree" to serializedTree
        )

        AccessibilityStreamHandler.sendEvent(payload)
    }

    /**
     * Serializa recursivamente um AccessibilityNodeInfo em um mapa estruturado,
     * incluindo metadados cruciais para auditoria e ações de RPA.
     */
    private fun serializeNodeSecurely(node: AccessibilityNodeInfo?): Map<String, Any?>? {
        if (node == null) return null

        val nodeMap = mutableMapOf<String, Any?>()

        try {
            nodeMap["className"] = node.className?.toString() ?: ""
            nodeMap["text"] = node.text?.toString() ?: ""
            nodeMap["contentDescription"] = node.contentDescription?.toString() ?: ""
            nodeMap["viewId"] = node.viewIdResourceName ?: ""
            nodeMap["clickable"] = node.isClickable
            nodeMap["focusable"] = node.isFocusable
            nodeMap["scrollable"] = node.isScrollable

            // Coleta os limites geométricos da view na tela
            val rect = android.graphics.Rect()
            node.getBoundsInScreen(rect)
            nodeMap["bounds"] = mapOf(
                "left" to rect.left,
                "top" to rect.top,
                "right" to rect.right,
                "bottom" to rect.bottom
            )
        } catch (e: Exception) {
            // Silencia erros de nós que perderam propriedades durante a renderização assíncrona
        }

        val childrenList = mutableListOf<Map<String, Any?>>()
        val childCount = try {
            node.childCount
        } catch (e: Exception) {
            0
        }

        for (i in 0 until childCount) {
            var childNode: AccessibilityNodeInfo? = null
            try {
                childNode = node.getChild(i)
                if (childNode != null) {
                    val childSerialized = serializeNodeSecurely(childNode)
                    if (childSerialized != null) {
                        childrenList.add(childSerialized)
                    }
                }
            } catch (e: Exception) {
                // Trata falhas de Binder ao obter filho
            } finally {
                try {
                    childNode?.recycle()
                } catch (e: Exception) {
                    // Silencia erro ao reciclar filho
                }
            }
        }

        if (childrenList.isNotEmpty()) {
            nodeMap["children"] = childrenList
        }

        return nodeMap
    }

    override fun onInterrupt() {
        Log.d(TAG, "Serviço de Acessibilidade interrompido!")
    }
}

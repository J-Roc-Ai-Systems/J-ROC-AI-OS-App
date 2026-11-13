package online.jrocai.phone.data

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

data class ChatMessage(val role: String, val text: String, val timestamp: Long = System.currentTimeMillis())

class ConversationStore(context: Context) {
    private val prefs = context.getSharedPreferences("jrocai_conversations", Context.MODE_PRIVATE)

    @Synchronized
    fun load(): List<ChatMessage> {
        val raw = prefs.getString("messages", "[]") ?: "[]"
        return try {
            val array = JSONArray(raw)
            (0 until array.length()).mapNotNull { index ->
                array.optJSONObject(index)?.let {
                    ChatMessage(it.optString("role"), it.optString("text"), it.optLong("timestamp"))
                }
            }
        } catch (_: Exception) {
            emptyList()
        }
    }

    @Synchronized
    fun append(message: ChatMessage) {
        val all = load().takeLast(199).toMutableList().apply { add(message) }
        val array = JSONArray()
        all.forEach { array.put(JSONObject().put("role", it.role).put("text", it.text).put("timestamp", it.timestamp)) }
        prefs.edit().putString("messages", array.toString()).apply()
    }

    fun clear() {
        prefs.edit().remove("messages").apply()
    }
}

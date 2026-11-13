package online.jrocai.phone.data

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

class OpenAiClient {
    private val http = OkHttpClient.Builder()
        .callTimeout(90, TimeUnit.SECONDS)
        .build()
    private val jsonType = "application/json; charset=utf-8".toMediaType()
    private val baseUrl = "https://api.openai.com/v1"

    fun listModels(apiKey: String): List<String> {
        val request = Request.Builder()
            .url("$baseUrl/models")
            .header("Authorization", "Bearer $apiKey")
            .get()
            .build()
        http.newCall(request).execute().use { response ->
            val body = response.body?.string().orEmpty()
            if (!response.isSuccessful) throw IOException(errorMessage(body, response.code))
            val data = JSONObject(body).optJSONArray("data") ?: JSONArray()
            return (0 until data.length()).mapNotNull { data.optJSONObject(it)?.optString("id") }
                .filter { it.isNotBlank() && (it.startsWith("gpt-") || it.startsWith("o")) }
                .sorted()
        }
    }

    fun respond(apiKey: String, model: String, prompt: String, repairMode: Boolean): String {
        val instructions = if (repairMode) {
            "You are J-Bot, the J-ROC AI device troubleshooting and repair assistant. " +
                "Ask for the device model and symptoms when missing. Give safe, stepwise diagnostics. " +
                "Do not claim to unlock, bypass security, or perform a repair you cannot verify. " +
                "Recommend backing up data and obtaining consent before actions that may erase data."
        } else {
            "You are J-ROC AI Assistant, a precise and helpful personal AI assistant."
        }
        val payload = JSONObject()
            .put("model", model)
            .put("instructions", instructions)
            .put("input", prompt)
            .put("store", false)
        val request = Request.Builder()
            .url("$baseUrl/responses")
            .header("Authorization", "Bearer $apiKey")
            .header("Content-Type", "application/json")
            .post(payload.toString().toRequestBody(jsonType))
            .build()
        http.newCall(request).execute().use { response ->
            val body = response.body?.string().orEmpty()
            if (!response.isSuccessful) throw IOException(errorMessage(body, response.code))
            val result = JSONObject(body)
            result.optString("output_text").takeIf { it.isNotBlank() }?.let { return it }
            val output = result.optJSONArray("output") ?: JSONArray()
            val parts = mutableListOf<String>()
            for (i in 0 until output.length()) {
                val content = output.optJSONObject(i)?.optJSONArray("content") ?: continue
                for (j in 0 until content.length()) {
                    content.optJSONObject(j)?.optString("text")?.takeIf { it.isNotBlank() }?.let(parts::add)
                }
            }
            return parts.joinToString("\n").ifBlank { "The model returned no text. Please try again." }
        }
    }

    private fun errorMessage(body: String, status: Int): String = try {
        JSONObject(body).optJSONObject("error")?.optString("message")
            ?.takeIf { it.isNotBlank() } ?: "OpenAI request failed (HTTP $status)."
    } catch (_: Exception) {
        "OpenAI request failed (HTTP $status)."
    }
}

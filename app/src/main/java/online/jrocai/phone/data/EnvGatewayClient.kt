package online.jrocai.phone.data

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

/** Talks only to the J-ROC AI backend. The OpenAI provider key never enters the APK. */
class EnvGatewayClient {
    private val http = OkHttpClient.Builder().callTimeout(90, TimeUnit.SECONDS).build()
    private val jsonType = "application/json; charset=utf-8".toMediaType()

    fun listModels(baseUrl: String, gatewayToken: String): List<String> {
        val request = Request.Builder()
            .url(baseUrl.trimEnd('/') + "/v1/models")
            .header("Authorization", "Bearer $gatewayToken")
            .get().build()
        http.newCall(request).execute().use { response ->
            val body = response.body?.string().orEmpty()
            if (!response.isSuccessful) throw IOException(errorMessage(body, response.code))
            val data = JSONObject(body).optJSONArray("data") ?: JSONArray()
            return (0 until data.length()).mapNotNull { data.optJSONObject(it)?.optString("id") }
                .filter { it.isNotBlank() }.sorted()
        }
    }

    fun respond(baseUrl: String, gatewayToken: String, model: String, prompt: String, repairMode: Boolean): String {
        val payload = JSONObject()
            .put("model", model)
            .put("message", prompt)
            .put("agent", if (repairMode) "jbot" else "assistant")
        val request = Request.Builder()
            .url(baseUrl.trimEnd('/') + "/v1/chat")
            .header("Authorization", "Bearer $gatewayToken")
            .header("Content-Type", "application/json")
            .post(payload.toString().toRequestBody(jsonType)).build()
        http.newCall(request).execute().use { response ->
            val body = response.body?.string().orEmpty()
            if (!response.isSuccessful) throw IOException(errorMessage(body, response.code))
            return JSONObject(body).optString("reply").ifBlank { "The J-ROC AI gateway returned an empty response." }
        }
    }

    fun health(baseUrl: String): String {
        val request = Request.Builder().url(baseUrl.trimEnd('/') + "/health").get().build()
        http.newCall(request).execute().use { response ->
            if (!response.isSuccessful) throw IOException("Gateway health check failed (HTTP ${response.code}).")
            return response.body?.string().orEmpty()
        }
    }

    private fun errorMessage(body: String, status: Int): String = try {
        JSONObject(body).optString("detail").ifBlank { "J-ROC AI gateway request failed (HTTP $status)." }
    } catch (_: Exception) {
        "J-ROC AI gateway request failed (HTTP $status)."
    }
}

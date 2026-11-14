package online.jrocai.phone.data

import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

/** Authenticated client for the Waves 11–15 platform catalogue. */
class WaveElevenFifteenPlatformClient {
    private val http = OkHttpClient.Builder().callTimeout(20, TimeUnit.SECONDS).build()

    fun load(baseUrl: String, token: String): JSONObject {
        require(baseUrl.startsWith("https://") || baseUrl.startsWith("http://10.0.2.2") || baseUrl.startsWith("http://127.0.0.1")) {
            "Use HTTPS for remote platform connections."
        }
        require(token.isNotBlank()) { "Save the platform gateway token in secure settings first." }
        val request = Request.Builder()
            .url(baseUrl.trimEnd('/') + "/platform/v1/waves/11-15")
            .header("Authorization", "Bearer $token")
            .get().build()
        http.newCall(request).execute().use { response ->
            val body = response.body?.string().orEmpty()
            if (!response.isSuccessful) throw IOException("Waves 11–15 request failed (HTTP " + response.code + ").")
            return JSONObject(body)
        }
    }

    fun loadCollections(baseUrl: String, token: String): JSONObject {
        require(baseUrl.startsWith("https://") || baseUrl.startsWith("http://10.0.2.2") || baseUrl.startsWith("http://127.0.0.1")) {
            "Use HTTPS for remote platform connections."
        }
        require(token.isNotBlank()) { "Save the platform gateway token in secure settings first." }
        val request = Request.Builder()
            .url(baseUrl.trimEnd('/') + "/platform/v1/wave-eleven-fifteen/catalog")
            .header("Authorization", "Bearer $token")
            .get().build()
        http.newCall(request).execute().use { response ->
            val body = response.body?.string().orEmpty()
            if (!response.isSuccessful) throw IOException("Service catalogue request failed (HTTP " + response.code + ").")
            return JSONObject(body)
        }
    }
}

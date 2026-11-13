package online.jrocai.phone.data

import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.IOException
import java.util.concurrent.TimeUnit
import org.json.JSONArray
import org.json.JSONObject

/** Authenticated read-only client for live J-ROC AI platform operations. */
class PlatformOperationsClient {
    private val http = OkHttpClient.Builder()
        .callTimeout(15, TimeUnit.SECONDS)
        .connectTimeout(5, TimeUnit.SECONDS)
        .build()

    fun status(baseUrl: String, token: String): JSONObject =
        getObject(baseUrl, token, "/platform/v1/status")

    fun services(baseUrl: String, token: String): JSONArray =
        getArray(baseUrl, token, "/platform/v1/services")

    fun workflows(baseUrl: String, token: String): JSONArray =
        getArray(baseUrl, token, "/platform/v1/workflows")

    fun localModelStatus(baseUrl: String, token: String): JSONObject =
        getObject(baseUrl, token, "/platform/v1/local-models/status")

    fun repairProfiles(baseUrl: String, token: String): JSONArray =
        getArray(baseUrl, token, "/platform/v1/repair/profiles")

    fun buildRuns(baseUrl: String, token: String): JSONArray =
        getArray(baseUrl, token, "/platform/v1/builds/runs")

    fun releaseChannels(baseUrl: String, token: String): JSONArray =
        getArray(baseUrl, token, "/platform/v1/releases/channels")

    private fun request(baseUrl: String, token: String, path: String): String {
        val root = baseUrl.trim().trimEnd('/')
        if (!root.startsWith("https://") &&
            !root.startsWith("http://127.0.0.1") &&
            !root.startsWith("http://localhost") &&
            !root.startsWith("http://10.0.2.2")) {
            throw IOException("Use HTTPS for remote Env Agent connections.")
        }
        if (token.isBlank()) throw IOException("Env Agent access token is not configured.")
        val request = Request.Builder()
            .url(root + path)
            .header("Authorization", "Bearer $token")
            .get()
            .build()
        http.newCall(request).execute().use { response ->
            val body = response.body?.string().orEmpty()
            if (!response.isSuccessful) {
                throw IOException("Platform request failed (HTTP ${response.code}).")
            }
            return body
        }
    }

    private fun getObject(baseUrl: String, token: String, path: String): JSONObject =
        JSONObject(request(baseUrl, token, path))

    private fun getArray(baseUrl: String, token: String, path: String): JSONArray =
        JSONArray(request(baseUrl, token, path))
}

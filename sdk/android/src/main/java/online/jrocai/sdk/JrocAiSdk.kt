package online.jrocai.sdk

import android.os.Handler
import android.os.Looper
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL
import java.nio.charset.StandardCharsets
import java.util.concurrent.Executors

/** First-party asynchronous client for the platform-wide J-ROC AI service gateway. */
class JrocAiSdk(
    baseUrl: String,
    private val tokenProvider: AccessTokenProvider,
    private val connectTimeoutMs: Int = 10_000,
    private val readTimeoutMs: Int = 20_000
) {
    private val endpoint = baseUrl.trimEnd('/')
    private val executor = Executors.newFixedThreadPool(2)
    private val mainHandler = Handler(Looper.getMainLooper())

    fun checkHealth(callback: SdkCallback<JSONObject>) = request("GET", "/health", null, callback)

    fun submitSourceTask(
        agentId: String,
        taskType: String,
        repository: String,
        description: String,
        callback: SdkCallback<AgentTask>
    ) {
        val body = JSONObject().put("agent_id", agentId).put("task_type", taskType)
            .put("repository", repository).put("description", description)
        request("POST", "/v1/tasks", body, object : SdkCallback<JSONObject> {
            override fun onComplete(result: SdkResult<JSONObject>) {
                val json = result.value
                if (json == null) {
                    callback.onComplete(SdkResult(error = result.error))
                    return
                }
                try {
                    callback.onComplete(SdkResult(value = AgentTask(
                        taskId = json.getString("task_id"),
                        agentId = json.getString("agent_id"),
                        taskType = json.getString("task_type"),
                        status = json.getString("status"),
                        requiresApproval = json.optBoolean("requires_approval", false),
                        createdAt = json.optString("created_at").takeIf { it.isNotBlank() }
                    )))
                } catch (e: Exception) {
                    callback.onComplete(SdkResult(error = SdkError("INVALID_RESPONSE", e.message ?: "Invalid response")))
                }
            }
        })
    }

    private fun request(method: String, path: String, body: JSONObject?, callback: SdkCallback<JSONObject>) {
        executor.execute {
            var connection: HttpURLConnection? = null
            val result: SdkResult<JSONObject> = try {
                val token = tokenProvider.getAccessToken()
                if (path != "/health" && token.isNullOrBlank()) {
                    throw SdkRequestException("AUTH_REQUIRED", "A session access token is required.")
                }
                connection = (URL(endpoint + path).openConnection() as HttpURLConnection).apply {
                    requestMethod = method
                    connectTimeout = connectTimeoutMs
                    readTimeout = readTimeoutMs
                    setRequestProperty("Accept", "application/json")
                    if (!token.isNullOrBlank()) setRequestProperty("Authorization", "Bearer $token")
                    if (body != null) {
                        doOutput = true
                        setRequestProperty("Content-Type", "application/json; charset=utf-8")
                    }
                }
                if (body != null) connection.outputStream.use {
                    it.write(body.toString().toByteArray(StandardCharsets.UTF_8))
                }
                val status = connection.responseCode
                val stream = if (status in 200..299) connection.inputStream else connection.errorStream
                val text = stream?.use { BufferedReader(InputStreamReader(it, StandardCharsets.UTF_8)).readText() }.orEmpty()
                if (status !in 200..299) {
                    val message = try { JSONObject(text).optString("message", "Request failed") }
                    catch (_: Exception) { "Request failed" }
                    SdkResult(error = SdkError("HTTP_ERROR", message, status))
                } else SdkResult(value = JSONObject(text))
            } catch (e: SdkRequestException) {
                SdkResult(error = SdkError(e.code, e.message ?: "Request failed"))
            } catch (e: Exception) {
                SdkResult(error = SdkError("NETWORK_ERROR", e.message ?: "Network request failed"))
            } finally {
                connection?.disconnect()
            }
            mainHandler.post { callback.onComplete(result) }
        }
    }

    private class SdkRequestException(val code: String, message: String) : Exception(message)
    fun close() { executor.shutdown() }
}

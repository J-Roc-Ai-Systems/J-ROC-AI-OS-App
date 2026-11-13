package online.jrocai.phone.data

import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

/** Authenticated Wave Six through Ten API client. Tokens are read from encrypted settings. */
class WaveSixTenPlatformClient {
    private val http=OkHttpClient.Builder().callTimeout(20,TimeUnit.SECONDS).build()
    fun load(baseUrl:String,token:String):JSONObject {
        require(baseUrl.startsWith("https://") || baseUrl.startsWith("http://10.0.2.2") || baseUrl.startsWith("http://127.0.0.1")) {
            "Use HTTPS for remote platform connections."
        }
        require(token.isNotBlank()) { "Save the platform gateway token in secure settings first." }
        val request=Request.Builder().url(baseUrl.trimEnd('/')+"/platform/v1/waves/6-10")
            .header("Authorization","Bearer $token").get().build()
        http.newCall(request).execute().use { response ->
            val body=response.body?.string().orEmpty()
            if(!response.isSuccessful) throw IOException("Platform request failed (HTTP "+response.code+").")
            return JSONObject(body)
        }
    }
    fun loadAgents(baseUrl:String,token:String):JSONObject {
        val request=Request.Builder().url(baseUrl.trimEnd('/')+"/platform/v1/agents")
            .header("Authorization","Bearer $token").get().build()
        http.newCall(request).execute().use { response ->
            val body=response.body?.string().orEmpty()
            if(!response.isSuccessful) throw IOException("Agent registry request failed (HTTP "+response.code+").")
            return JSONObject(body)
        }
    }
}

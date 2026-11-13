package online.jrocai.phone.data

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

/** User-owned memory API; requires the separate account session token. */
class MemoryClient {
    private val http=OkHttpClient.Builder().callTimeout(20,TimeUnit.SECONDS).build()
    private val jsonType="application/json; charset=utf-8".toMediaType()

    fun list(baseUrl:String,token:String):JSONArray = request(baseUrl,token,"/identity/v1/memory",null,"GET")
    fun create(baseUrl:String,token:String,category:String,title:String,content:String):JSONObject {
        val body=JSONObject().put("category",category).put("title",title).put("content",content).put("source","user-entered")
        return JSONObject(request(baseUrl,token,"/identity/v1/memory",body,"POST"))
    }
    fun delete(baseUrl:String,token:String,memoryId:String):JSONObject =
        JSONObject(request(baseUrl,token,"/identity/v1/memory/"+memoryId,null,"DELETE"))

    private fun request(baseUrl:String,token:String,path:String,body:JSONObject?,method:String):String {
        val root=baseUrl.trim().trimEnd('/')
        if(!root.startsWith("https://") && !root.startsWith("http://127.0.0.1") &&
            !root.startsWith("http://localhost") && !root.startsWith("http://10.0.2.2")) {
            throw IOException("Use HTTPS for remote account connections.")
        }
        if(token.isBlank())throw IOException("Sign in to use personal memory.")
        val builder=Request.Builder().url(root+path).header("Authorization","Bearer $token")
        when(method) {
            "POST" -> builder.header("Content-Type","application/json").post((body ?: JSONObject()).toString().toRequestBody(jsonType))
            "DELETE" -> builder.delete()
            else -> builder.get()
        }
        http.newCall(builder.build()).execute().use { response ->
            val raw=response.body?.string().orEmpty()
            if(!response.isSuccessful) {
                val message=runCatching { JSONObject(raw).optString("detail") }.getOrNull().orEmpty()
                throw IOException(message.ifBlank { "Memory request failed (HTTP ${response.code})." })
            }
            return raw
        }
    }
}

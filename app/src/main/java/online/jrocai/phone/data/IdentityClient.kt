package online.jrocai.phone.data

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

/** Account API client. Session tokens are persisted only through Android Keystore-backed settings. */
class IdentityClient {
    private val http=OkHttpClient.Builder().callTimeout(20,TimeUnit.SECONDS).build()
    private val jsonType="application/json; charset=utf-8".toMediaType()

    fun register(baseUrl:String,email:String,displayName:String,password:String):JSONObject =
        post(baseUrl,"/identity/v1/register",JSONObject().put("email",email).put("display_name",displayName).put("password",password),null)
    fun login(baseUrl:String,email:String,password:String):JSONObject =
        post(baseUrl,"/identity/v1/login",JSONObject().put("email",email).put("password",password),null)
    fun me(baseUrl:String,token:String):JSONObject = request(baseUrl,"/identity/v1/me",token,null)
    fun logout(baseUrl:String,token:String):JSONObject = post(baseUrl,"/identity/v1/logout",JSONObject(),token)

    private fun post(baseUrl:String,path:String,body:JSONObject,token:String?):JSONObject =
        request(baseUrl,path,token,body)
    private fun request(baseUrl:String,path:String,token:String?,body:JSONObject?):JSONObject {
        val root=baseUrl.trim().trimEnd('/')
        if(!root.startsWith("https://") && !root.startsWith("http://127.0.0.1") &&
            !root.startsWith("http://localhost") && !root.startsWith("http://10.0.2.2")) {
            throw IOException("Use HTTPS for remote account connections.")
        }
        val builder=Request.Builder().url(root+path).header("Accept","application/json")
        if(token!=null) builder.header("Authorization","Bearer $token")
        if(body!=null) builder.header("Content-Type","application/json")
            .post(body.toString().toRequestBody(jsonType))
        else builder.get()
        http.newCall(builder.build()).execute().use { response ->
            val raw=response.body?.string().orEmpty()
            if(!response.isSuccessful) {
                val message=runCatching { JSONObject(raw).optString("detail") }.getOrNull().orEmpty()
                throw IOException(message.ifBlank { "Account request failed (HTTP ${response.code})." })
            }
            return JSONObject(raw.ifBlank { "{}" })
        }
    }
}

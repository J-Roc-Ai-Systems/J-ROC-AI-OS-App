package online.jrocai.phone.data

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

/** Gateway-authenticated J-Bot diagnostic session API. */
class RepairClient {
    private val http=OkHttpClient.Builder().callTimeout(20,TimeUnit.SECONDS).build()
    private val jsonType="application/json; charset=utf-8".toMediaType()
    fun profiles(baseUrl:String,token:String)=JSONArray(request(baseUrl,token,"/platform/v1/repair/profiles",null,"GET"))
    fun sessions(baseUrl:String,token:String)=JSONArray(request(baseUrl,token,"/platform/v1/repair/sessions",null,"GET"))
    fun start(baseUrl:String,token:String,issue:String,method:String,deviceId:String,profileId:String):JSONObject {
        val body=JSONObject().put("issue_summary",issue).put("connection_method",method)
        if(deviceId.isNotBlank())body.put("device_id",deviceId)
        if(profileId.isNotBlank())body.put("profile_id",profileId)
        return JSONObject(request(baseUrl,token,"/platform/v1/repair/sessions",body,"POST"))
    }
    private fun request(baseUrl:String,token:String,path:String,body:JSONObject?,method:String):String {
        val root=baseUrl.trim().trimEnd('/')
        if(!root.startsWith("https://") && !root.startsWith("http://127.0.0.1") &&
            !root.startsWith("http://localhost") && !root.startsWith("http://10.0.2.2")) {
            throw IOException("Use HTTPS for remote Env Agent connections.")
        }
        if(token.isBlank())throw IOException("Env Agent gateway access is not configured.")
        val builder=Request.Builder().url(root+path).header("Authorization","Bearer $token")
        if(body!=null)builder.header("Content-Type","application/json").post(body.toString().toRequestBody(jsonType))
        else builder.get()
        http.newCall(builder.build()).execute().use { response ->
            val raw=response.body?.string().orEmpty()
            if(!response.isSuccessful) {
                val message=runCatching { JSONObject(raw).optString("detail") }.getOrNull().orEmpty()
                throw IOException(message.ifBlank { "Repair request failed (HTTP ${response.code})." })
            }
            return raw
        }
    }
}

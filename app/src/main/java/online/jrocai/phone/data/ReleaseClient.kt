package online.jrocai.phone.data

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import org.json.JSONArray
import java.io.IOException
import java.util.concurrent.TimeUnit

class ReleaseClient {
    private val http=OkHttpClient.Builder().callTimeout(20,TimeUnit.SECONDS).build()
    private val jsonType="application/json; charset=utf-8".toMediaType()
    fun channels(base:String,token:String)=JSONArray(call(base,token,"/platform/v1/releases/channels",null))
    fun releases(base:String,token:String)=JSONArray(call(base,token,"/platform/v1/releases",null))
    fun createChannel(base:String,token:String,id:String,name:String,stability:String)=JSONObject(call(base,token,"/platform/v1/releases/channels",
        JSONObject().put("channel_id",id).put("name",name).put("stability",stability)))
    fun createRelease(base:String,token:String,id:String,appId:String,version:String,channel:String,artifact:String,revision:String,notes:String)=JSONObject(call(base,token,
        "/platform/v1/releases",JSONObject().put("release_id",id).put("application_id",appId).put("version",version).put("channel_id",channel).put("artifact_reference",artifact).put("source_revision",revision).put("notes",notes)))
    fun approve(base:String,token:String,id:String)=JSONObject(call(base,token,"/platform/v1/releases/$id/approve",JSONObject()))
    fun publish(base:String,token:String,id:String)=JSONObject(call(base,token,"/platform/v1/releases/$id/publish",JSONObject()))
    private fun call(base:String,token:String,path:String,body:JSONObject?):String {
        val root=base.trim().trimEnd('/')
        if(!root.startsWith("https://") && !root.startsWith("http://127.0.0.1") && !root.startsWith("http://localhost") && !root.startsWith("http://10.0.2.2"))throw IOException("Use HTTPS for remote Env Agent connections.")
        if(token.isBlank())throw IOException("Env Agent gateway access is not configured.")
        val builder=Request.Builder().url(root+path).header("Authorization","Bearer $token")
        if(body!=null)builder.header("Content-Type","application/json").post(body.toString().toRequestBody(jsonType)) else builder.get()
        http.newCall(builder.build()).execute().use { response ->
            val raw=response.body?.string().orEmpty()
            if(!response.isSuccessful){val message=runCatching{JSONObject(raw).optString("detail")}.getOrNull().orEmpty();throw IOException(message.ifBlank{"Release request failed (HTTP ${response.code})."})}
            return raw
        }
    }
}

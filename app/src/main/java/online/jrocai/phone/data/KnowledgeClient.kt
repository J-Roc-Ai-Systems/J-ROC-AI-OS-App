package online.jrocai.phone.data

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.net.URLEncoder
import java.util.concurrent.TimeUnit

class KnowledgeClient {
    private val http=OkHttpClient.Builder().callTimeout(25,TimeUnit.SECONDS).build()
    private val jsonType="application/json; charset=utf-8".toMediaType()
    fun search(base:String,token:String,query:String)=JSONArray(call(base,token,"/platform/v1/knowledge/search?q="+URLEncoder.encode(query,"UTF-8"),null))
    fun add(base:String,token:String,title:String,source:String,content:String)=JSONObject(call(base,token,"/platform/v1/knowledge",
        JSONObject().put("title",title).put("source_reference",source).put("content",content)))
    private fun call(base:String,token:String,path:String,body:JSONObject?):String {
        val root=base.trim().trimEnd('/')
        if(!root.startsWith("https://") && !root.startsWith("http://127.0.0.1") && !root.startsWith("http://localhost") && !root.startsWith("http://10.0.2.2"))throw IOException("Use HTTPS for remote Env Agent connections.")
        if(token.isBlank())throw IOException("Env Agent gateway access is not configured.")
        val builder=Request.Builder().url(root+path).header("Authorization","Bearer $token")
        if(body!=null)builder.header("Content-Type","application/json").post(body.toString().toRequestBody(jsonType)) else builder.get()
        http.newCall(builder.build()).execute().use { response ->
            val raw=response.body?.string().orEmpty()
            if(!response.isSuccessful){val message=runCatching{JSONObject(raw).optString("detail")}.getOrNull().orEmpty();throw IOException(message.ifBlank{"Knowledge request failed (HTTP ${response.code})."})}
            return raw
        }
    }
}

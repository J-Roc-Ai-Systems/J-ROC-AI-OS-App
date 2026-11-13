package online.jrocai.phone.data

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

class FileClient {
    private val http=OkHttpClient.Builder().callTimeout(30,TimeUnit.SECONDS).build()
    private val jsonType="application/json; charset=utf-8".toMediaType()
    fun list(base:String,token:String)=JSONArray(call(base,token,"/identity/v1/files",null,"GET"))
    fun upload(base:String,token:String,name:String,type:String,base64:String)=JSONObject(call(base,token,"/identity/v1/files",
        JSONObject().put("name",name).put("content_type",type).put("content_base64",base64),"POST"))
    fun delete(base:String,token:String,id:String)=JSONObject(call(base,token,"/identity/v1/files/$id",null,"DELETE"))
    private fun call(base:String,token:String,path:String,body:JSONObject?,method:String):String {
        val root=base.trim().trimEnd('/')
        if(!root.startsWith("https://") && !root.startsWith("http://127.0.0.1") && !root.startsWith("http://localhost") && !root.startsWith("http://10.0.2.2"))throw IOException("Use HTTPS for remote account connections.")
        if(token.isBlank())throw IOException("Sign in to manage encrypted files.")
        val builder=Request.Builder().url(root+path).header("Authorization","Bearer $token")
        if(body!=null)builder.header("Content-Type","application/json").post(body.toString().toRequestBody(jsonType))
        else if(method=="DELETE")builder.delete() else builder.get()
        http.newCall(builder.build()).execute().use { response ->
            val raw=response.body?.string().orEmpty()
            if(!response.isSuccessful){val message=runCatching{JSONObject(raw).optString("detail")}.getOrNull().orEmpty();throw IOException(message.ifBlank{"File request failed (HTTP ${response.code})."})}
            return raw
        }
    }
}

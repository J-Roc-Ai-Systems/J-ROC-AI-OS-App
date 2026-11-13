package online.jrocai.phone.data

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

class EnterpriseClient {
    private val http=OkHttpClient.Builder().callTimeout(20,TimeUnit.SECONDS).build()
    private val jsonType="application/json; charset=utf-8".toMediaType()
    fun organizations(base:String,token:String)=JSONArray(call(base,token,"/platform/v1/enterprise/organizations",null))
    fun createOrganization(base:String,token:String,id:String,name:String,plan:String)=JSONObject(call(base,token,"/platform/v1/enterprise/organizations",
        JSONObject().put("organization_id",id).put("name",name).put("plan",plan)))
    fun devices(base:String,token:String,id:String)=JSONArray(call(base,token,"/platform/v1/enterprise/organizations/$id/devices",null))
    fun enrollDevice(base:String,token:String,org:String,id:String,name:String,platform:String,manufacturer:String,model:String)=JSONObject(call(base,token,
        "/platform/v1/enterprise/organizations/$org/devices",JSONObject().put("device_id",id).put("display_name",name).put("platform",platform).put("manufacturer",manufacturer).put("model",model)))
    private fun call(base:String,token:String,path:String,body:JSONObject?):String {
        val root=base.trim().trimEnd('/')
        if(!root.startsWith("https://") && !root.startsWith("http://127.0.0.1") && !root.startsWith("http://localhost") && !root.startsWith("http://10.0.2.2"))throw IOException("Use HTTPS for remote Env Agent connections.")
        if(token.isBlank())throw IOException("Env Agent gateway access is not configured.")
        val builder=Request.Builder().url(root+path).header("Authorization","Bearer $token")
        if(body!=null)builder.header("Content-Type","application/json").post(body.toString().toRequestBody(jsonType)) else builder.get()
        http.newCall(builder.build()).execute().use { response ->
            val raw=response.body?.string().orEmpty()
            if(!response.isSuccessful){val message=runCatching{JSONObject(raw).optString("detail")}.getOrNull().orEmpty();throw IOException(message.ifBlank{"Enterprise request failed (HTTP ${response.code})."})}
            return raw
        }
    }
}

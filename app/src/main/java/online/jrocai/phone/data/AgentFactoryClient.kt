package online.jrocai.phone.data

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

/** Gateway-authenticated agent definition and version control client. */
class AgentFactoryClient {
    private val http=OkHttpClient.Builder().callTimeout(20,TimeUnit.SECONDS).build()
    private val jsonType="application/json; charset=utf-8".toMediaType()
    fun list(base:String,token:String)=JSONArray(request(base,token,"/platform/v1/agents",null,"GET"))
    fun create(base:String,token:String,id:String,name:String,purpose:String,capabilities:List<String>,permissions:List<String>,workerCapability:String):JSONObject {
        val body=JSONObject().put("agent_id",id).put("name",name).put("purpose",purpose)
            .put("capabilities",JSONArray(capabilities)).put("permissions",JSONArray(permissions))
            .put("worker_capability",workerCapability).put("configuration",JSONObject())
        return JSONObject(request(base,token,"/platform/v1/agents",body,"POST"))
    }
    fun publish(base:String,token:String,id:String)=JSONObject(request(base,token,"/platform/v1/agents/$id/publish",JSONObject(),"POST"))
    fun disable(base:String,token:String,id:String)=JSONObject(request(base,token,"/platform/v1/agents/$id/disable",JSONObject(),"POST"))
    private fun request(base:String,token:String,path:String,body:JSONObject?,method:String):String {
        val root=base.trim().trimEnd('/')
        if(!root.startsWith("https://") && !root.startsWith("http://127.0.0.1") &&
            !root.startsWith("http://localhost") && !root.startsWith("http://10.0.2.2"))throw IOException("Use HTTPS for remote Env Agent connections.")
        if(token.isBlank())throw IOException("Env Agent gateway access is not configured.")
        val builder=Request.Builder().url(root+path).header("Authorization","Bearer $token")
        if(body!=null)builder.header("Content-Type","application/json").post(body.toString().toRequestBody(jsonType))
        else if(method=="POST")builder.post(JSONObject().toString().toRequestBody(jsonType))
        else builder.get()
        http.newCall(builder.build()).execute().use { response ->
            val raw=response.body?.string().orEmpty()
            if(!response.isSuccessful) {
                val message=runCatching { JSONObject(raw).optString("detail") }.getOrNull().orEmpty()
                throw IOException(message.ifBlank { "Agent request failed (HTTP ${response.code})." })
            }
            return raw
        }
    }
}

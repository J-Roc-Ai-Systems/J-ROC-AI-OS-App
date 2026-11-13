package online.jrocai.phone.data

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

/** Application Factory registry and approval-gated build queue client. */
class FactoryClient {
    private val http=OkHttpClient.Builder().callTimeout(25,TimeUnit.SECONDS).build()
    private val jsonType="application/json; charset=utf-8".toMediaType()
    fun projects(base:String,token:String)=JSONArray(call(base,token,"/platform/v1/projects",null))
    fun recipes(base:String,token:String)=JSONArray(call(base,token,"/platform/v1/builds/recipes",null))
    fun runs(base:String,token:String)=JSONArray(call(base,token,"/platform/v1/builds/runs",null))
    fun createProject(base:String,token:String,name:String,type:String,platforms:List<String>,description:String):JSONObject {
        val body=JSONObject().put("project_name",name).put("project_type",type).put("target_platforms",JSONArray(platforms)).put("description",description)
        return JSONObject(call(base,token,"/platform/v1/projects",body))
    }
    fun createRecipe(base:String,token:String,id:String,name:String,platform:String,command:List<String>,directory:String,capability:String):JSONObject {
        val body=JSONObject().put("recipe_id",id).put("name",name).put("platform",platform)
            .put("build_command",JSONArray(command)).put("working_directory",directory).put("required_capability",capability)
        return JSONObject(call(base,token,"/platform/v1/builds/recipes",body))
    }
    fun requestBuild(base:String,token:String,projectId:String,recipeId:String,revision:String):JSONObject {
        val body=JSONObject().put("project_id",projectId).put("recipe_id",recipeId).put("source_revision",revision)
        return JSONObject(call(base,token,"/platform/v1/builds/runs",body))
    }
    fun approveBuild(base:String,token:String,runId:String):JSONObject =
        JSONObject(call(base,token,"/platform/v1/builds/runs/$runId/approve",JSONObject()))
    private fun call(base:String,token:String,path:String,body:JSONObject?):String {
        val root=base.trim().trimEnd('/')
        if(!root.startsWith("https://") && !root.startsWith("http://127.0.0.1") &&
            !root.startsWith("http://localhost") && !root.startsWith("http://10.0.2.2"))throw IOException("Use HTTPS for remote Env Agent connections.")
        if(token.isBlank())throw IOException("Env Agent gateway access is not configured.")
        val builder=Request.Builder().url(root+path).header("Authorization","Bearer $token")
        if(body!=null)builder.header("Content-Type","application/json").post(body.toString().toRequestBody(jsonType)) else builder.get()
        http.newCall(builder.build()).execute().use { response ->
            val raw=response.body?.string().orEmpty()
            if(!response.isSuccessful) {
                val message=runCatching { JSONObject(raw).optString("detail") }.getOrNull().orEmpty()
                throw IOException(message.ifBlank { "Application Factory request failed (HTTP ${response.code})." })
            }
            return raw
        }
    }
}

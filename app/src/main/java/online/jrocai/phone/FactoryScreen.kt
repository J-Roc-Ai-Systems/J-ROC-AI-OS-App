package online.jrocai.phone

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import online.jrocai.phone.data.FactoryClient
import online.jrocai.phone.data.SecureSettings
import org.json.JSONArray
import org.json.JSONObject

@Composable
fun FactoryScreen(settings:SecureSettings,client:FactoryClient,onBack:()->Unit,runOnMain:((()->Unit))->Unit) {
    var projectName by remember { mutableStateOf("") }
    var projectType by remember { mutableStateOf("android") }
    var platform by remember { mutableStateOf("android") }
    var recipeId by remember { mutableStateOf("android.debug") }
    var recipeName by remember { mutableStateOf("Android Debug Build") }
    var workingDirectory by remember { mutableStateOf("workspace/project") }
    var command by remember { mutableStateOf("gradle :app:assembleDebug") }
    var revision by remember { mutableStateOf("") }
    var selectedProject by remember { mutableStateOf("") }
    var selectedRecipe by remember { mutableStateOf("android.debug") }
    var projects by remember { mutableStateOf(listOf<JSONObject>()) }
    var runs by remember { mutableStateOf(listOf<JSONObject>()) }
    var status by remember { mutableStateOf("Projects and build requests require the Environment Agent administrator token.") }
    var busy by remember { mutableStateOf(false) }

    fun refresh() {
        val base=settings.readGatewayUrl();val token=settings.readGatewayToken()
        if(token.isBlank()){status="Configure the Environment Agent gateway token in Model Center.";return}
        if(busy)return
        busy=true
        Thread {
            val result=runCatching { client.projects(base,token) to client.runs(base,token) }
            runOnMain {
                result.onSuccess { pair ->
                    projects=(0 until pair.first.length()).mapNotNull{pair.first.optJSONObject(it)}
                    runs=(0 until pair.second.length()).mapNotNull{pair.second.optJSONObject(it)}
                    if(selectedProject.isBlank() && projects.isNotEmpty())selectedProject=projects.first().optString("project_id")
                    status="Loaded ${projects.size} projects and ${runs.size} build runs."
                }.onFailure{status=it.message ?: "Application Factory unavailable."}
                busy=false
            }
        }.start()
    }
    Surface(modifier=Modifier.fillMaxSize(),color=Color(0xFF0B0F14)) {
        Column(modifier=Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(18.dp),verticalArrangement=Arrangement.spacedBy(10.dp)) {
            Row(modifier=Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) {
                Column {
                    Text("APPLICATION FACTORY",color=Color.White,fontSize=20.sp,fontWeight=FontWeight.Bold)
                    Text("Projects • recipes • approval-gated build jobs",color=Color(0xFF00B3FF),fontSize=11.sp)
                }
                Button(onClick=onBack){Text("Back")}
            }
            Card(colors=CardDefaults.cardColors(containerColor=Color(0xFF151C25)),modifier=Modifier.fillMaxWidth()) {
                Column(Modifier.padding(13.dp),verticalArrangement=Arrangement.spacedBy(7.dp)) {
                    Text("CREATE PROJECT",color=Color(0xFF00B3FF),fontSize=10.sp,fontWeight=FontWeight.Bold)
                    OutlinedTextField(value=projectName,onValueChange={projectName=it},label={Text("Project name")},modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=projectType,onValueChange={projectType=it},label={Text("Project type")},modifier=Modifier.fillMaxWidth())
                    Button(enabled=!busy && projectName.length>=2,modifier=Modifier.fillMaxWidth(),onClick={
                        val base=settings.readGatewayUrl();val token=settings.readGatewayToken();val name=projectName.trim();val type=projectType.trim()
                        if(!busy && token.isNotBlank()) {
                            busy=true
                            Thread {
                                val result=runCatching { client.createProject(base,token,name,type,listOf(platform),"Created from Android Application Factory") to client.projects(base,token) }
                                runOnMain {
                                    result.onSuccess { pair -> selectedProject=pair.first.optString("project_id");projects=(0 until pair.second.length()).mapNotNull{pair.second.optJSONObject(it)};projectName="";status="Project registered." }
                                        .onFailure{status=it.message ?: "Project creation failed."}
                                    busy=false
                                }
                            }.start()
                        }
                    }){Text("Create Project")}
                }
            }
            Card(colors=CardDefaults.cardColors(containerColor=Color(0xFF151C25)),modifier=Modifier.fillMaxWidth()) {
                Column(Modifier.padding(13.dp),verticalArrangement=Arrangement.spacedBy(7.dp)) {
                    Text("REGISTER BUILD RECIPE",color=Color(0xFF00B3FF),fontSize=10.sp,fontWeight=FontWeight.Bold)
                    OutlinedTextField(value=recipeId,onValueChange={recipeId=it},label={Text("Recipe identifier")},modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=recipeName,onValueChange={recipeName=it},label={Text("Recipe name")},modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=platform,onValueChange={platform=it},label={Text("Target platform")},modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=workingDirectory,onValueChange={workingDirectory=it},label={Text("Working directory")},modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=command,onValueChange={command=it},label={Text("Command tokens (space separated)")},modifier=Modifier.fillMaxWidth())
                    Button(enabled=!busy && recipeId.isNotBlank() && command.isNotBlank(),modifier=Modifier.fillMaxWidth(),onClick={
                        val base=settings.readGatewayUrl();val token=settings.readGatewayToken()
                        if(!busy && token.isNotBlank()) {
                            busy=true
                            Thread {
                                val result=runCatching { client.createRecipe(base,token,recipeId.trim(),recipeName.trim(),platform.trim(),command.trim().split(Regex("\\s+")),workingDirectory.trim(),"build.execute") }
                                runOnMain { result.onSuccess{status="Build recipe registered."}.onFailure{status=it.message ?: "Recipe registration failed."};busy=false }
                            }.start()
                        }
                    }){Text("Save Build Recipe")}
                }
            }
            Card(colors=CardDefaults.cardColors(containerColor=Color(0xFF151C25)),modifier=Modifier.fillMaxWidth()) {
                Column(Modifier.padding(13.dp),verticalArrangement=Arrangement.spacedBy(7.dp)) {
                    Text("REQUEST A BUILD",color=Color(0xFF00B3FF),fontSize=10.sp,fontWeight=FontWeight.Bold)
                    OutlinedTextField(value=selectedProject,onValueChange={selectedProject=it},label={Text("Project identifier")},modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=selectedRecipe,onValueChange={selectedRecipe=it},label={Text("Recipe identifier")},modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=revision,onValueChange={revision=it},label={Text("Source revision (commit)")},modifier=Modifier.fillMaxWidth())
                    Button(enabled=!busy && selectedProject.isNotBlank() && selectedRecipe.isNotBlank() && revision.length>=7,modifier=Modifier.fillMaxWidth(),onClick={
                        val base=settings.readGatewayUrl();val token=settings.readGatewayToken()
                        if(!busy && token.isNotBlank()) {
                            busy=true
                            Thread {
                                val result=runCatching { client.requestBuild(base,token,selectedProject.trim(),selectedRecipe.trim(),revision.trim()) to client.runs(base,token) }
                                runOnMain { result.onSuccess{pair->runs=(0 until pair.second.length()).mapNotNull{pair.second.optJSONObject(it)};status="Build request created in pending approval state."}.onFailure{status=it.message ?: "Build request failed."};busy=false }
                            }.start()
                        }
                    }){Text("Request Build (Approval Required)")}
                    Button(enabled=!busy,modifier=Modifier.fillMaxWidth(),onClick={refresh()}){Text("Refresh Projects and Build Runs")}
                    Text(status,color=Color(0xFFAAB6C5),fontSize=12.sp)
                }
            }
            runs.forEach { run ->
                val id=run.optString("run_id")
                Card(colors=CardDefaults.cardColors(containerColor=Color(0xFF151C25)),modifier=Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(12.dp),verticalArrangement=Arrangement.spacedBy(5.dp)) {
                        Text("Build run $id",color=Color.White,fontWeight=FontWeight.Bold)
                        Text("Project: "+run.optString("project_id")+" • State: "+run.optString("state"),color=Color(0xFFAAB6C5),fontSize=11.sp)
                        if(run.optString("state")=="pending_approval") Button(enabled=!busy,onClick={
                            val base=settings.readGatewayUrl();val token=settings.readGatewayToken()
                            if(!busy){busy=true;Thread{val result=runCatching{client.approveBuild(base,token,id) to client.runs(base,token)};runOnMain{result.onSuccess{pair->runs=(0 until pair.second.length()).mapNotNull{pair.second.optJSONObject(it)};status="Build approved and queued for an eligible worker."}.onFailure{status=it.message ?: "Build approval failed."};busy=false}}.start()}
                        }){Text("Approve and Queue")}
                    }
                }
            }
        }
    }
}

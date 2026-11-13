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
import online.jrocai.phone.data.AgentFactoryClient
import online.jrocai.phone.data.SecureSettings
import org.json.JSONArray
import org.json.JSONObject

@Composable
fun AgentFactoryScreen(settings:SecureSettings,client:AgentFactoryClient,onBack:()->Unit,runOnMain:((()->Unit))->Unit) {
    var agentId by remember { mutableStateOf("") }
    var name by remember { mutableStateOf("") }
    var purpose by remember { mutableStateOf("") }
    var capability by remember { mutableStateOf("platform.read") }
    var permissions by remember { mutableStateOf("platform.read") }
    var workerCapability by remember { mutableStateOf("agent.execute") }
    var agents by remember { mutableStateOf(listOf<JSONObject>()) }
    var status by remember { mutableStateOf("Agent definitions are versioned and permission-bounded. No generated code is executed by this screen.") }
    var busy by remember { mutableStateOf(false) }
    fun refresh() {
        val base=settings.readGatewayUrl();val token=settings.readGatewayToken()
        if(token.isBlank()){status="Configure the Env Agent gateway token in Model Center.";return}
        if(busy)return
        busy=true
        Thread {
            val result=runCatching { client.list(base,token) }
            runOnMain {
                result.onSuccess { data -> agents=(0 until data.length()).mapNotNull { data.optJSONObject(it) };status="Loaded ${agents.size} agent definitions." }
                    .onFailure { status=it.message ?: "Agent registry unavailable." }
                busy=false
            }
        }.start()
    }
    Surface(modifier=Modifier.fillMaxSize(),color=Color(0xFF0B0F14)) {
        Column(modifier=Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(18.dp),verticalArrangement=Arrangement.spacedBy(10.dp)) {
            Row(modifier=Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) {
                Column {
                    Text("AGENT FACTORY",color=Color.White,fontSize=21.sp,fontWeight=FontWeight.Bold)
                    Text("Versioned agents • permission allowlist",color=Color(0xFF00B3FF),fontSize=11.sp)
                }
                Button(onClick=onBack){Text("Back")}
            }
            Card(colors=CardDefaults.cardColors(containerColor=Color(0xFF151C25)),modifier=Modifier.fillMaxWidth()) {
                Column(Modifier.padding(14.dp),verticalArrangement=Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(value=agentId,onValueChange={agentId=it},label={Text("Agent identifier")},singleLine=true,modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=name,onValueChange={name=it},label={Text("Agent name")},singleLine=true,modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=purpose,onValueChange={purpose=it},label={Text("Purpose")},minLines=2,maxLines=4,modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=capability,onValueChange={capability=it},label={Text("Capabilities, comma separated")},modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=permissions,onValueChange={permissions=it},label={Text("Permissions, comma separated")},modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=workerCapability,onValueChange={workerCapability=it},label={Text("Worker capability")},singleLine=true,modifier=Modifier.fillMaxWidth())
                    Button(enabled=!busy && agentId.isNotBlank() && name.isNotBlank() && purpose.length>=5,modifier=Modifier.fillMaxWidth(),onClick={
                        val base=settings.readGatewayUrl();val token=settings.readGatewayToken()
                        val id=agentId.trim();val agentName=name.trim();val why=purpose.trim()
                        val caps=capability.split(",").map{it.trim()}.filter{it.isNotBlank()}
                        val perms=permissions.split(",").map{it.trim()}.filter{it.isNotBlank()}
                        if(token.isBlank())status="Configure the Env Agent gateway token in Model Center."
                        else {
                            busy=true
                            Thread {
                                val result=runCatching { client.create(base,token,id,agentName,why,caps,perms,workerCapability.trim());client.list(base,token) }
                                runOnMain {
                                    result.onSuccess { data -> agents=(0 until data.length()).mapNotNull{data.optJSONObject(it)};status="Agent draft version created. Review and publish it when approved." }
                                        .onFailure { status=it.message ?: "Agent definition failed." }
                                    busy=false
                                }
                            }.start()
                        }
                    }){Text("Create Agent Draft")}
                    Button(enabled=!busy,modifier=Modifier.fillMaxWidth(),onClick={refresh()}){Text("Refresh Agent Registry")}
                    Text(status,color=Color(0xFFAAB6C5),fontSize=12.sp)
                }
            }
            agents.forEach { agent ->
                val id=agent.optString("agent_id")
                val current=agent.optJSONObject("current")
                Card(colors=CardDefaults.cardColors(containerColor=Color(0xFF151C25)),modifier=Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(13.dp),verticalArrangement=Arrangement.spacedBy(5.dp)) {
                        Text(agent.optString("name"),color=Color.White,fontWeight=FontWeight.Bold)
                        Text("$id • State: ${agent.optString("state")} • Version: ${agent.optInt("current_version")}",color=Color(0xFFAAB6C5),fontSize=11.sp)
                        Text(agent.optString("purpose"),color=Color(0xFFAAB6C5),fontSize=12.sp)
                        Text("Permissions: "+(current?.optJSONArray("permissions") ?: JSONArray()).toString(),color=Color(0xFFAAB6C5),fontSize=10.sp)
                        Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                            Button(enabled=!busy,onClick={
                                val base=settings.readGatewayUrl();val token=settings.readGatewayToken()
                                if(!busy){busy=true;Thread{val result=runCatching{client.publish(base,token,id);client.list(base,token)};runOnMain{result.onSuccess{data->agents=(0 until data.length()).mapNotNull{data.optJSONObject(it)};status="Agent version published."}.onFailure{status=it.message ?: "Publish failed."};busy=false}}.start()}
                            }){Text("Publish")}
                            Button(enabled=!busy,onClick={
                                val base=settings.readGatewayUrl();val token=settings.readGatewayToken()
                                if(!busy){busy=true;Thread{val result=runCatching{client.disable(base,token,id);client.list(base,token)};runOnMain{result.onSuccess{data->agents=(0 until data.length()).mapNotNull{data.optJSONObject(it)};status="Agent disabled."}.onFailure{status=it.message ?: "Disable failed."};busy=false}}.start()}
                            }){Text("Disable")}
                        }
                    }
                }
            }
        }
    }
}

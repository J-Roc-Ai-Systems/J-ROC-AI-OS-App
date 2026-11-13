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
import online.jrocai.phone.data.RepairClient
import online.jrocai.phone.data.SecureSettings
import org.json.JSONArray
import org.json.JSONObject

@Composable
fun RepairScreen(settings:SecureSettings,client:RepairClient,onBack:()->Unit,runOnMain:((()->Unit))->Unit) {
    var issue by remember { mutableStateOf("") }
    var deviceId by remember { mutableStateOf("") }
    var profileId by remember { mutableStateOf("") }
    var method by remember { mutableStateOf("usb") }
    var profiles by remember { mutableStateOf(listOf<JSONObject>()) }
    var sessions by remember { mutableStateOf(listOf<JSONObject>()) }
    var status by remember { mutableStateOf("Connect to the Env Agent to load repair profiles and sessions.") }
    var busy by remember { mutableStateOf(false) }

    fun refresh() {
        val base=settings.readGatewayUrl();val token=settings.readGatewayToken()
        if(token.isBlank()){status="Configure the Env Agent gateway token in Model Center.";return}
        if(busy)return
        busy=true
        Thread {
            val result=runCatching { client.profiles(base,token) to client.sessions(base,token) }
            runOnMain {
                result.onSuccess { pair ->
                    profiles=(0 until pair.first.length()).mapNotNull { pair.first.optJSONObject(it) }
                    sessions=(0 until pair.second.length()).mapNotNull { pair.second.optJSONObject(it) }
                    status="Loaded ${profiles.size} compatibility profiles and ${sessions.size} diagnostic sessions."
                }.onFailure { status=it.message ?: "Repair workspace could not be loaded." }
                busy=false
            }
        }.start()
    }
    Surface(modifier=Modifier.fillMaxSize(),color=Color(0xFF0B0F14)) {
        Column(modifier=Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(18.dp),verticalArrangement=Arrangement.spacedBy(10.dp)) {
            Row(modifier=Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) {
                Column {
                    Text("J-BOT REPAIR WORKSPACE",color=Color.White,fontSize=20.sp,fontWeight=FontWeight.Bold)
                    Text("Non-invasive USB, wireless and local diagnostics",color=Color(0xFF00B3FF),fontSize=11.sp)
                }
                Button(onClick=onBack){Text("Back")}
            }
            Card(colors=CardDefaults.cardColors(containerColor=Color(0xFF151C25)),modifier=Modifier.fillMaxWidth()) {
                Column(Modifier.padding(14.dp),verticalArrangement=Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(value=issue,onValueChange={issue=it},label={Text("Describe device issue")},minLines=3,maxLines=5,modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=deviceId,onValueChange={deviceId=it},label={Text("Registered device identifier (optional)")},singleLine=true,modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=profileId,onValueChange={profileId=it},label={Text("Compatibility profile identifier (optional)")},singleLine=true,modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=method,onValueChange={method=it},label={Text("Connection method: usb, wireless or local-only")},singleLine=true,modifier=Modifier.fillMaxWidth())
                    Button(enabled=!busy && issue.trim().length>=5,modifier=Modifier.fillMaxWidth(),onClick={
                        val base=settings.readGatewayUrl();val token=settings.readGatewayToken()
                        if(token.isBlank())status="Configure the Env Agent gateway token in Model Center."
                        else {
                            val description=issue.trim();val device=deviceId.trim();val profile=profileId.trim();val connection=method.trim()
                            busy=true
                            Thread {
                                val result=runCatching {
                                    client.start(base,token,description,connection,device,profile)
                                    client.sessions(base,token)
                                }
                                runOnMain {
                                    result.onSuccess { data ->
                                        sessions=(0 until data.length()).mapNotNull { data.optJSONObject(it) }
                                        issue=""
                                        status="Diagnostic session created. No device action has been performed."
                                    }.onFailure { status=it.message ?: "Diagnostic session could not be created." }
                                    busy=false
                                }
                            }.start()
                        }
                    }){Text("Create Diagnostic Session")}
                    Button(enabled=!busy,modifier=Modifier.fillMaxWidth(),onClick={refresh()}){Text("Refresh Profiles and Sessions")}
                    Text(status,color=Color(0xFFAAB6C5),fontSize=12.sp)
                }
            }
            Text("COMPATIBILITY PROFILES",color=Color(0xFF00B3FF),fontSize=10.sp,fontWeight=FontWeight.Bold)
            profiles.forEach { profile ->
                Card(colors=CardDefaults.cardColors(containerColor=Color(0xFF151C25)),modifier=Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(12.dp),verticalArrangement=Arrangement.spacedBy(4.dp)) {
                        Text(profile.optString("manufacturer")+" "+profile.optString("model"),color=Color.White,fontWeight=FontWeight.Bold)
                        Text("Profile: "+profile.optString("profile_id")+" • "+profile.optString("operating_system"),color=Color(0xFFAAB6C5),fontSize=11.sp)
                        Text("Methods: "+(profile.optJSONArray("supported_methods") ?: JSONArray()).toString(),color=Color(0xFFAAB6C5),fontSize=11.sp)
                    }
                }
            }
            Text("DIAGNOSTIC SESSIONS",color=Color(0xFF00B3FF),fontSize=10.sp,fontWeight=FontWeight.Bold)
            sessions.forEach { session ->
                Card(colors=CardDefaults.cardColors(containerColor=Color(0xFF151C25)),modifier=Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(12.dp),verticalArrangement=Arrangement.spacedBy(4.dp)) {
                        Text(session.optString("issue_summary"),color=Color.White,fontWeight=FontWeight.SemiBold)
                        Text("Session: "+session.optString("session_id"),color=Color(0xFFAAB6C5),fontSize=10.sp)
                        Text("State: "+session.optString("state")+" • Method: "+session.optString("connection_method"),color=Color(0xFF00B3FF),fontSize=11.sp)
                    }
                }
            }
        }
    }
}

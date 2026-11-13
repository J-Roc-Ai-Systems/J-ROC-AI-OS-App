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
import online.jrocai.phone.data.ReleaseClient
import online.jrocai.phone.data.SecureSettings
import org.json.JSONObject

@Composable
fun ReleaseScreen(settings:SecureSettings,client:ReleaseClient,onBack:()->Unit,runOnMain:((()->Unit))->Unit) {
    var channelId by remember { mutableStateOf("development") }
    var channelName by remember { mutableStateOf("Development") }
    var stability by remember { mutableStateOf("development") }
    var releaseId by remember { mutableStateOf("") }
    var applicationId by remember { mutableStateOf("") }
    var version by remember { mutableStateOf("") }
    var artifact by remember { mutableStateOf("") }
    var revision by remember { mutableStateOf("") }
    var notes by remember { mutableStateOf("") }
    var channels by remember { mutableStateOf(listOf<JSONObject>()) }
    var releases by remember { mutableStateOf(listOf<JSONObject>()) }
    var status by remember { mutableStateOf("Release records require gateway administrator approval. Publishing here marks distribution readiness only.") }
    var busy by remember { mutableStateOf(false) }
    fun refresh() {
        val base=settings.readGatewayUrl();val token=settings.readGatewayToken()
        if(token.isBlank()){status="Configure the Environment Agent gateway token in Model Center.";return}
        if(busy)return
        busy=true
        Thread {
            val result=runCatching { client.channels(base,token) to client.releases(base,token) }
            runOnMain {
                result.onSuccess{pair->channels=(0 until pair.first.length()).mapNotNull{pair.first.optJSONObject(it)};releases=(0 until pair.second.length()).mapNotNull{pair.second.optJSONObject(it)};status="Loaded ${channels.size} release channels and ${releases.size} releases."}
                    .onFailure{status=it.message ?: "Release registry unavailable."}
                busy=false
            }
        }.start()
    }
    Surface(modifier=Modifier.fillMaxSize(),color=Color(0xFF0B0F14)) {
        Column(modifier=Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(18.dp),verticalArrangement=Arrangement.spacedBy(10.dp)) {
            Row(modifier=Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) {
                Column {
                    Text("RELEASE MANAGEMENT",color=Color.White,fontSize=20.sp,fontWeight=FontWeight.Bold)
                    Text("Channels • approvals • distribution readiness",color=Color(0xFF00B3FF),fontSize=11.sp)
                }
                Button(onClick=onBack){Text("Back")}
            }
            Card(colors=CardDefaults.cardColors(containerColor=Color(0xFF151C25)),modifier=Modifier.fillMaxWidth()) {
                Column(Modifier.padding(13.dp),verticalArrangement=Arrangement.spacedBy(7.dp)) {
                    Text("CREATE RELEASE CHANNEL",color=Color(0xFF00B3FF),fontSize=10.sp,fontWeight=FontWeight.Bold)
                    OutlinedTextField(value=channelId,onValueChange={channelId=it},label={Text("Channel identifier")},modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=channelName,onValueChange={channelName=it},label={Text("Channel name")},modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=stability,onValueChange={stability=it},label={Text("development, preview, stable or long_term_support")},modifier=Modifier.fillMaxWidth())
                    Button(enabled=!busy && channelId.length>=2 && channelName.length>=2,modifier=Modifier.fillMaxWidth(),onClick={
                        val base=settings.readGatewayUrl();val token=settings.readGatewayToken()
                        if(token.isNotBlank()&&!busy){busy=true;Thread{val result=runCatching{client.createChannel(base,token,channelId.trim(),channelName.trim(),stability.trim());client.channels(base,token)};runOnMain{result.onSuccess{data->channels=(0 until data.length()).mapNotNull{data.optJSONObject(it)};status="Release channel saved."}.onFailure{status=it.message ?: "Channel creation failed."};busy=false}}.start()}
                    }){Text("Save Channel")}
                }
            }
            Card(colors=CardDefaults.cardColors(containerColor=Color(0xFF151C25)),modifier=Modifier.fillMaxWidth()) {
                Column(Modifier.padding(13.dp),verticalArrangement=Arrangement.spacedBy(7.dp)) {
                    Text("REGISTER RELEASE",color=Color(0xFF00B3FF),fontSize=10.sp,fontWeight=FontWeight.Bold)
                    OutlinedTextField(value=releaseId,onValueChange={releaseId=it},label={Text("Release identifier")},modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=applicationId,onValueChange={applicationId=it},label={Text("Registered application identifier")},modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=version,onValueChange={version=it},label={Text("Version")},modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=channelId,onValueChange={channelId=it},label={Text("Release channel identifier")},modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=artifact,onValueChange={artifact=it},label={Text("Artifact reference")},modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=revision,onValueChange={revision=it},label={Text("Source revision")},modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=notes,onValueChange={notes=it},label={Text("Release notes")},modifier=Modifier.fillMaxWidth())
                    Button(enabled=!busy && releaseId.isNotBlank() && applicationId.isNotBlank() && version.isNotBlank() && artifact.isNotBlank() && revision.length>=7,modifier=Modifier.fillMaxWidth(),onClick={
                        val base=settings.readGatewayUrl();val token=settings.readGatewayToken()
                        if(token.isNotBlank()&&!busy){busy=true;Thread{val result=runCatching{client.createRelease(base,token,releaseId.trim(),applicationId.trim(),version.trim(),channelId.trim(),artifact.trim(),revision.trim(),notes.trim());client.releases(base,token)};runOnMain{result.onSuccess{data->releases=(0 until data.length()).mapNotNull{data.optJSONObject(it)};status="Release registered in pending approval state."}.onFailure{status=it.message ?: "Release registration failed."};busy=false}}.start()}
                    }){Text("Register Release")}
                    Button(enabled=!busy,modifier=Modifier.fillMaxWidth(),onClick={refresh()}){Text("Refresh Release Registry")}
                    Text(status,color=Color(0xFFAAB6C5),fontSize=12.sp)
                }
            }
            releases.forEach { release ->
                val id=release.optString("release_id")
                Card(colors=CardDefaults.cardColors(containerColor=Color(0xFF151C25)),modifier=Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(12.dp),verticalArrangement=Arrangement.spacedBy(5.dp)) {
                        Text(release.optString("application_id")+" • "+release.optString("version"),color=Color.White,fontWeight=FontWeight.Bold)
                        Text("$id • "+release.optString("state"),color=Color(0xFFAAB6C5),fontSize=11.sp)
                        if(release.optString("state")=="pending_approval")Button(enabled=!busy,onClick={
                            val base=settings.readGatewayUrl();val token=settings.readGatewayToken()
                            if(token.isNotBlank()&&!busy){busy=true;Thread{val result=runCatching{client.approve(base,token,id);client.releases(base,token)};runOnMain{result.onSuccess{data->releases=(0 until data.length()).mapNotNull{data.optJSONObject(it)};status="Release approved."}.onFailure{status=it.message ?: "Release approval failed."};busy=false}}.start()}
                        }){Text("Approve")}
                        if(release.optString("state")=="approved")Button(enabled=!busy,onClick={
                            val base=settings.readGatewayUrl();val token=settings.readGatewayToken()
                            if(token.isNotBlank()&&!busy){busy=true;Thread{val result=runCatching{client.publish(base,token,id);client.releases(base,token)};runOnMain{result.onSuccess{data->releases=(0 until data.length()).mapNotNull{data.optJSONObject(it)};status="Release marked ready for distribution. No deployment occurred."}.onFailure{status=it.message ?: "Release publish step failed."};busy=false}}.start()}
                        }){Text("Mark Distribution Ready")}
                    }
                }
            }
        }
    }
}

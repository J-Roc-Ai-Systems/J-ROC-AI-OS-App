package online.jrocai.phone

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import online.jrocai.phone.data.PlatformOperationsClient
import online.jrocai.phone.data.SecureSettings

private data class WaveCardData(val number:Int,val title:String,val scope:String,val state:String)
private data class PlatformSnapshot(
    val serviceName:String,val serviceCount:Int,val serviceNames:String,val localModelState:String,
    val workflowCount:Int,val repairProfileCount:Int,val buildRunCount:Int,val releaseChannelCount:Int
)

@Composable
fun PlatformHub(
    onBack:()->Unit,
    settings:SecureSettings,
    operations:PlatformOperationsClient,
    runOnMain:((()->Unit))->Unit
) {
    var loading by remember { mutableStateOf(false) }
    var connection by remember { mutableStateOf("Not connected") }
    var serviceCount by remember { mutableStateOf(0) }
    var serviceNames by remember { mutableStateOf("") }
    var localModelState by remember { mutableStateOf("Not checked") }
    var workflowCount by remember { mutableStateOf(0) }
    var repairProfileCount by remember { mutableStateOf(0) }
    var buildRunCount by remember { mutableStateOf(0) }
    var releaseChannelCount by remember { mutableStateOf(0) }
    var error by remember { mutableStateOf("") }
    val waves=listOf(
        WaveCardData(1,"Android Phone Foundation","Command center, assistant, J-Bot, settings and local history","Existing app foundation"),
        WaveCardData(2,"Intelligence and Production","Brain, services, workers, integrations and platform registry","Backend foundations committed"),
        WaveCardData(3,"Identity and Security","Accounts, sessions, roles, privacy and access controls","Identity API foundation added"),
        WaveCardData(4,"Model Center and Local Intelligence","Local models, model routing, memory and spending policy","Loopback model adapter added"),
        WaveCardData(5,"J-Bot Repair Intelligence","Compatibility, device diagnostics and safe repair workflows","Diagnostic API foundation added"),
        WaveCardData(6,"Agent and Workflow Factory","Agent definitions, worker lifecycle and orchestration","Workflow state engine added"),
        WaveCardData(7,"Application Factory","Project workspaces, build recipes and artifact workflows","Approval-gated build queue added"),
        WaveCardData(8,"Knowledge, Files and Communications","Knowledge, encrypted storage, notifications and synchronization","Encrypted account file API added"),
        WaveCardData(9,"Enterprise and Fleet Operations","Organizations, fleet enrollment, policies and monitoring","Enterprise registry foundations added"),
        WaveCardData(10,"Release and Quality","Release channels, approvals, packaging, updates and final quality","Release registry foundations added")
    )
    val refresh:()->Unit={
        if(!loading){
            loading=true
            error=""
            Thread {
                val result=runCatching {
                    val base=settings.readGatewayUrl()
                    val token=settings.readGatewayToken()
                    val status=operations.status(base,token)
                    val services=operations.services(base,token)
                    val local=runCatching { operations.localModelStatus(base,token) }.getOrNull()
                    val workflows=runCatching { operations.workflows(base,token).length() }.getOrDefault(0)
                    val repairs=runCatching { operations.repairProfiles(base,token).length() }.getOrDefault(0)
                    val builds=runCatching { operations.buildRuns(base,token).length() }.getOrDefault(0)
                    val releases=runCatching { operations.releaseChannels(base,token).length() }.getOrDefault(0)
                    PlatformSnapshot(
                        status.optString("service","Platform connected"),services.length(),
                        (0 until services.length()).mapNotNull { services.optJSONObject(it)?.optString("display_name") }.take(5).joinToString(", "),
                        if(local==null) "Not available" else if(local.optBoolean("available")) "Available" else "Offline",
                        workflows,repairs,builds,releases
                    )
                }
                runOnMain {
                    result.onSuccess { snapshot ->
                        connection=snapshot.serviceName
                        serviceCount=snapshot.serviceCount
                        serviceNames=snapshot.serviceNames
                        localModelState=snapshot.localModelState
                        workflowCount=snapshot.workflowCount
                        repairProfileCount=snapshot.repairProfileCount
                        buildRunCount=snapshot.buildRunCount
                        releaseChannelCount=snapshot.releaseChannelCount
                    }.onFailure { error=it.message ?: "Platform connection failed." }
                    loading=false
                }
            }.start()
        }
    }
    Surface(modifier=Modifier.fillMaxSize(),color=Color(0xFF0B0F14)) {
        Column(modifier=Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(18.dp),verticalArrangement=Arrangement.spacedBy(11.dp)) {
            Row(modifier=Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) {
                Column {
                    Text("J-ROC AI",color=Color.White,fontSize=24.sp,fontWeight=FontWeight.Bold)
                    Text("TEN-WAVE BUILD COMMAND",color=Color(0xFF00B3FF),fontSize=10.sp,fontWeight=FontWeight.Bold)
                }
                Button(onClick=onBack){Text("Back")}
            }
            Card(colors=CardDefaults.cardColors(containerColor=Color(0xFF142333)),modifier=Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp),verticalArrangement=Arrangement.spacedBy(7.dp)) {
                    Text("100 IMPLEMENTATION BATCHES",color=Color(0xFF00B3FF),fontWeight=FontWeight.Bold,fontSize=11.sp)
                    Text("10 waves • one consolidated validation phase",color=Color.White,fontSize=18.sp,fontWeight=FontWeight.Bold)
                    Text("Live connection status is reported separately from implementation progress. A registered service is not proof that its full feature set is complete.",color=Color(0xFFAAB6C5),fontSize=12.sp)
                    Button(onClick=refresh,enabled=!loading,modifier=Modifier.fillMaxWidth()) {
                        if(loading) CircularProgressIndicator()
                        else Text("Connect to Environment Agent")
                    }
                    Text("Connection: $connection",color=Color(0xFFAAB6C5),fontSize=12.sp)
                    if(serviceCount>0) {
                        Text("Registered services: $serviceCount",color=Color(0xFF00B3FF),fontSize=12.sp)
                        Text(serviceNames,color=Color(0xFFAAB6C5),fontSize=11.sp)
                    }
                    if(serviceCount>0) {
                        Text("Local model runtime: $localModelState",color=Color(0xFFAAB6C5),fontSize=11.sp)
                        Text("Workflows: $workflowCount • Repair profiles: $repairProfileCount",color=Color(0xFFAAB6C5),fontSize=11.sp)
                        Text("Build runs: $buildRunCount • Release channels: $releaseChannelCount",color=Color(0xFFAAB6C5),fontSize=11.sp)
                    }
                    if(error.isNotBlank()) Text(error,color=Color(0xFFFFB86B),fontSize=12.sp)
                }
            }
            waves.forEach { wave ->
                Card(colors=CardDefaults.cardColors(containerColor=Color(0xFF151C25)),modifier=Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(14.dp),verticalArrangement=Arrangement.spacedBy(5.dp)) {
                        Text("WAVE ${wave.number}  •  BATCHES ${(wave.number-1)*10+1}–${wave.number*10}",color=Color(0xFF00B3FF),fontSize=10.sp,fontWeight=FontWeight.Bold)
                        Text(wave.title,color=Color.White,fontSize=16.sp,fontWeight=FontWeight.SemiBold)
                        Text(wave.scope,color=Color(0xFFAAB6C5),fontSize=12.sp)
                        Text(wave.state,color=Color(0xFFFFC266),fontSize=11.sp)
                    }
                }
            }
            Spacer(Modifier.height(8.dp))
            Text("J-ROC AI • Local-first • Zero-dollar cloud spending gate",color=Color(0xFFAAB6C5),fontSize=11.sp)
        }
    }
}

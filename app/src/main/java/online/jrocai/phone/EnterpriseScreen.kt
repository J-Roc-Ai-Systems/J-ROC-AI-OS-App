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
import online.jrocai.phone.data.EnterpriseClient
import online.jrocai.phone.data.SecureSettings
import org.json.JSONObject

@Composable
fun EnterpriseScreen(settings:SecureSettings,client:EnterpriseClient,onBack:()->Unit,runOnMain:((()->Unit))->Unit) {
    var orgId by remember { mutableStateOf("") }
    var orgName by remember { mutableStateOf("") }
    var deviceId by remember { mutableStateOf("") }
    var deviceName by remember { mutableStateOf("") }
    var platform by remember { mutableStateOf("android") }
    var manufacturer by remember { mutableStateOf("") }
    var model by remember { mutableStateOf("") }
    var organizations by remember { mutableStateOf(listOf<JSONObject>()) }
    var devices by remember { mutableStateOf(listOf<JSONObject>()) }
    var status by remember { mutableStateOf("Enterprise registry and fleet enrollment require the gateway administrator token.") }
    var busy by remember { mutableStateOf(false) }
    fun refresh() {
        val base=settings.readGatewayUrl();val token=settings.readGatewayToken()
        if(token.isBlank()){status="Configure the Environment Agent gateway token in Model Center.";return}
        if(busy)return
        busy=true
        Thread {
            val result=runCatching { client.organizations(base,token) }
            runOnMain {
                result.onSuccess{data->organizations=(0 until data.length()).mapNotNull{data.optJSONObject(it)};status="Loaded ${organizations.size} organizations."}
                    .onFailure{status=it.message ?: "Enterprise registry unavailable."}
                busy=false
            }
        }.start()
    }
    Surface(modifier=Modifier.fillMaxSize(),color=Color(0xFF0B0F14)) {
        Column(modifier=Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(18.dp),verticalArrangement=Arrangement.spacedBy(10.dp)) {
            Row(modifier=Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) {
                Column {
                    Text("ENTERPRISE OPERATIONS",color=Color.White,fontSize=20.sp,fontWeight=FontWeight.Bold)
                    Text("Organizations • fleet enrollment • device inventory",color=Color(0xFF00B3FF),fontSize=11.sp)
                }
                Button(onClick=onBack){Text("Back")}
            }
            Card(colors=CardDefaults.cardColors(containerColor=Color(0xFF151C25)),modifier=Modifier.fillMaxWidth()) {
                Column(Modifier.padding(13.dp),verticalArrangement=Arrangement.spacedBy(7.dp)) {
                    Text("CREATE ORGANIZATION",color=Color(0xFF00B3FF),fontSize=10.sp,fontWeight=FontWeight.Bold)
                    OutlinedTextField(value=orgId,onValueChange={orgId=it},label={Text("Organization identifier")},modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=orgName,onValueChange={orgName=it},label={Text("Organization name")},modifier=Modifier.fillMaxWidth())
                    Button(enabled=!busy && orgId.length>=2 && orgName.length>=2,modifier=Modifier.fillMaxWidth(),onClick={
                        val base=settings.readGatewayUrl();val token=settings.readGatewayToken()
                        if(token.isNotBlank()&&!busy){busy=true;Thread{val result=runCatching{client.createOrganization(base,token,orgId.trim(),orgName.trim(),"local");client.organizations(base,token)};runOnMain{result.onSuccess{data->organizations=(0 until data.length()).mapNotNull{data.optJSONObject(it)};status="Organization created."}.onFailure{status=it.message ?: "Organization creation failed."};busy=false}}.start()}
                    }){Text("Create Organization")}
                }
            }
            Card(colors=CardDefaults.cardColors(containerColor=Color(0xFF151C25)),modifier=Modifier.fillMaxWidth()) {
                Column(Modifier.padding(13.dp),verticalArrangement=Arrangement.spacedBy(7.dp)) {
                    Text("ENROLL FLEET DEVICE",color=Color(0xFF00B3FF),fontSize=10.sp,fontWeight=FontWeight.Bold)
                    OutlinedTextField(value=orgId,onValueChange={orgId=it},label={Text("Organization identifier")},modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=deviceId,onValueChange={deviceId=it},label={Text("Device identifier")},modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=deviceName,onValueChange={deviceName=it},label={Text("Device display name")},modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=platform,onValueChange={platform=it},label={Text("Platform")},modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=manufacturer,onValueChange={manufacturer=it},label={Text("Manufacturer")},modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=model,onValueChange={model=it},label={Text("Model")},modifier=Modifier.fillMaxWidth())
                    Button(enabled=!busy && orgId.isNotBlank() && deviceId.isNotBlank() && deviceName.isNotBlank(),modifier=Modifier.fillMaxWidth(),onClick={
                        val base=settings.readGatewayUrl();val token=settings.readGatewayToken();val org=orgId.trim()
                        if(token.isNotBlank()&&!busy){busy=true;Thread{val result=runCatching{client.enrollDevice(base,token,org,deviceId.trim(),deviceName.trim(),platform.trim(),manufacturer.trim(),model.trim()) to client.devices(base,token,org)};runOnMain{result.onSuccess{pair->devices=(0 until pair.second.length()).mapNotNull{pair.second.optJSONObject(it)};status="Device enrollment recorded as pending approval."}.onFailure{status=it.message ?: "Device enrollment failed."};busy=false}}.start()}
                    }){Text("Enroll Device")}
                    Button(enabled=!busy,modifier=Modifier.fillMaxWidth(),onClick={refresh()}){Text("Refresh Organizations")}
                    Text(status,color=Color(0xFFAAB6C5),fontSize=12.sp)
                }
            }
            organizations.forEach { org ->
                Card(colors=CardDefaults.cardColors(containerColor=Color(0xFF151C25)),modifier=Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(12.dp),verticalArrangement=Arrangement.spacedBy(4.dp)) {
                        Text(org.optString("name"),color=Color.White,fontWeight=FontWeight.Bold)
                        Text(org.optString("organization_id")+" • "+org.optString("plan")+" • "+org.optString("state"),color=Color(0xFFAAB6C5),fontSize=11.sp)
                    }
                }
            }
            devices.forEach { device ->
                Text(device.optString("display_name")+" • "+device.optString("state"),color=Color(0xFFAAB6C5),fontSize=11.sp)
            }
        }
    }
}

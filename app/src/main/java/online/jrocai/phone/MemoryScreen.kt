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
import online.jrocai.phone.data.MemoryClient
import online.jrocai.phone.data.SecureSettings
import org.json.JSONArray
import org.json.JSONObject

@Composable
fun MemoryScreen(settings:SecureSettings,client:MemoryClient,onBack:()->Unit,runOnMain:((()->Unit))->Unit) {
    var category by remember { mutableStateOf("general") }
    var title by remember { mutableStateOf("") }
    var content by remember { mutableStateOf("") }
    var items by remember { mutableStateOf(listOf<JSONObject>()) }
    var status by remember { mutableStateOf("Sign in to manage your private memory notes.") }
    var busy by remember { mutableStateOf(false) }

    fun loadItems(token:String,base:String):List<JSONObject> {
        val data=client.list(base,token)
        return (0 until data.length()).mapNotNull { data.optJSONObject(it) }
    }
    fun refresh() {
        val token=settings.readIdentityToken()
        if(token.isBlank()){status="Sign in on the Account screen before using memory.";return}
        if(busy)return
        busy=true
        Thread {
            val result=runCatching { loadItems(token,settings.readGatewayUrl()) }
            runOnMain {
                result.onSuccess { items=it;status="Loaded ${it.size} private memory notes." }
                    .onFailure { status=it.message ?: "Memory could not be loaded." }
                busy=false
            }
        }.start()
    }
    Surface(modifier=Modifier.fillMaxSize(),color=Color(0xFF0B0F14)) {
        Column(modifier=Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(18.dp),verticalArrangement=Arrangement.spacedBy(10.dp)) {
            Row(modifier=Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) {
                Column {
                    Text("PERSONAL MEMORY",color=Color.White,fontSize=21.sp,fontWeight=FontWeight.Bold)
                    Text("User-controlled account notes",color=Color(0xFF00B3FF),fontSize=11.sp)
                }
                Button(onClick=onBack){Text("Back")}
            }
            Card(colors=CardDefaults.cardColors(containerColor=Color(0xFF151C25)),modifier=Modifier.fillMaxWidth()) {
                Column(Modifier.padding(14.dp),verticalArrangement=Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(value=category,onValueChange={category=it},label={Text("Category")},singleLine=true,modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=title,onValueChange={title=it},label={Text("Title")},singleLine=true,modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=content,onValueChange={content=it},label={Text("Memory note")},minLines=3,maxLines=6,modifier=Modifier.fillMaxWidth())
                    Text("Notes are saved only when you submit them. Do not store passwords, access tokens or private keys. Notes are not automatically inserted into AI prompts.",color=Color(0xFFAAB6C5),fontSize=11.sp)
                    Button(enabled=!busy && title.isNotBlank() && content.isNotBlank() && category.isNotBlank(),modifier=Modifier.fillMaxWidth(),onClick={
                        val token=settings.readIdentityToken();val base=settings.readGatewayUrl()
                        val cat=category.trim();val name=title.trim();val note=content.trim()
                        if(token.isBlank())status="Sign in on the Account screen first."
                        else if(!busy) {
                            busy=true
                            Thread {
                                val result=runCatching { client.create(base,token,cat,name,note);loadItems(token,base) }
                                runOnMain {
                                    result.onSuccess { items=it;title="";content="";status="Memory note saved." }
                                        .onFailure { status=it.message ?: "Memory note could not be saved." }
                                    busy=false
                                }
                            }.start()
                        }
                    }){Text("Save Memory Note")}
                    Button(enabled=!busy,modifier=Modifier.fillMaxWidth(),onClick={refresh}){Text("Refresh Memory Notes")}
                    Text(status,color=Color(0xFFAAB6C5),fontSize=12.sp)
                }
            }
            items.forEach { item ->
                Card(colors=CardDefaults.cardColors(containerColor=Color(0xFF151C25)),modifier=Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(13.dp),verticalArrangement=Arrangement.spacedBy(5.dp)) {
                        Text(item.optString("title"),color=Color.White,fontWeight=FontWeight.Bold)
                        Text(item.optString("category"),color=Color(0xFF00B3FF),fontSize=10.sp)
                        Text(item.optString("content"),color=Color(0xFFAAB6C5),fontSize=12.sp)
                        Button(enabled=!busy,onClick={
                            val token=settings.readIdentityToken();val base=settings.readGatewayUrl();val id=item.optString("memory_id")
                            if(!busy) {
                                busy=true
                                Thread {
                                    val result=runCatching { client.delete(base,token,id);loadItems(token,base) }
                                    runOnMain {
                                        result.onSuccess { items=it;status="Memory note deleted." }
                                            .onFailure { status=it.message ?: "Memory note could not be deleted." }
                                        busy=false
                                    }
                                }.start()
                            }
                        }){Text("Delete Note")}
                    }
                }
            }
        }
    }
}

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
import online.jrocai.phone.data.KnowledgeClient
import online.jrocai.phone.data.SecureSettings
import org.json.JSONObject

@Composable
fun KnowledgeScreen(settings:SecureSettings,client:KnowledgeClient,onBack:()->Unit,runOnMain:((()->Unit))->Unit) {
    var query by remember { mutableStateOf("") }
    var title by remember { mutableStateOf("") }
    var source by remember { mutableStateOf("") }
    var content by remember { mutableStateOf("") }
    var results by remember { mutableStateOf(listOf<JSONObject>()) }
    var status by remember { mutableStateOf("Search indexed knowledge or add a source to the Environment Agent knowledge store.") }
    var busy by remember { mutableStateOf(false) }
    fun search() {
        val token=settings.readGatewayToken();val base=settings.readGatewayUrl();val term=query.trim()
        if(token.isBlank()){status="Configure the Environment Agent gateway token in Model Center.";return}
        if(term.length<2){status="Enter at least two characters to search.";return}
        if(busy)return
        busy=true
        Thread{val result=runCatching{client.search(base,token,term)};runOnMain{result.onSuccess{data->results=(0 until data.length()).mapNotNull{data.optJSONObject(it)};status="Found ${results.size} knowledge matches."}.onFailure{status=it.message ?: "Knowledge search failed."};busy=false}}.start()
    }
    Surface(modifier=Modifier.fillMaxSize(),color=Color(0xFF0B0F14)) {
        Column(modifier=Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(18.dp),verticalArrangement=Arrangement.spacedBy(10.dp)) {
            Row(modifier=Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) {
                Column {
                    Text("KNOWLEDGE CENTER",color=Color.White,fontSize=20.sp,fontWeight=FontWeight.Bold)
                    Text("Source registry • indexed search",color=Color(0xFF00B3FF),fontSize=11.sp)
                }
                Button(onClick=onBack){Text("Back")}
            }
            Card(colors=CardDefaults.cardColors(containerColor=Color(0xFF151C25)),modifier=Modifier.fillMaxWidth()) {
                Column(Modifier.padding(13.dp),verticalArrangement=Arrangement.spacedBy(7.dp)) {
                    OutlinedTextField(value=query,onValueChange={query=it},label={Text("Search knowledge")},modifier=Modifier.fillMaxWidth())
                    Button(enabled=!busy && query.trim().length>=2,modifier=Modifier.fillMaxWidth(),onClick={search()}){Text("Search")}
                }
            }
            Card(colors=CardDefaults.cardColors(containerColor=Color(0xFF151C25)),modifier=Modifier.fillMaxWidth()) {
                Column(Modifier.padding(13.dp),verticalArrangement=Arrangement.spacedBy(7.dp)) {
                    Text("ADD KNOWLEDGE SOURCE",color=Color(0xFF00B3FF),fontSize=10.sp,fontWeight=FontWeight.Bold)
                    OutlinedTextField(value=title,onValueChange={title=it},label={Text("Document title")},modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=source,onValueChange={source=it},label={Text("Source reference")},modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=content,onValueChange={content=it},label={Text("Text content")},minLines=4,maxLines=8,modifier=Modifier.fillMaxWidth())
                    Button(enabled=!busy && title.isNotBlank() && source.isNotBlank() && content.isNotBlank(),modifier=Modifier.fillMaxWidth(),onClick={
                        val token=settings.readGatewayToken();val base=settings.readGatewayUrl()
                        if(token.isBlank())status="Configure the Environment Agent gateway token in Model Center."
                        else if(!busy){busy=true;Thread{val result=runCatching{client.add(base,token,title.trim(),source.trim(),content.trim())};runOnMain{result.onSuccess{title="";source="";content="";status="Knowledge source indexed."}.onFailure{status=it.message ?: "Knowledge ingestion failed."};busy=false}}.start()}
                    }){Text("Add Knowledge Source")}
                    Text(status,color=Color(0xFFAAB6C5),fontSize=12.sp)
                }
            }
            results.forEach { item ->
                Card(colors=CardDefaults.cardColors(containerColor=Color(0xFF151C25)),modifier=Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(12.dp),verticalArrangement=Arrangement.spacedBy(5.dp)) {
                        Text(item.optString("title"),color=Color.White,fontWeight=FontWeight.Bold)
                        Text(item.optString("source_reference"),color=Color(0xFF00B3FF),fontSize=10.sp)
                        Text(item.optString("excerpt",item.optString("content")),color=Color(0xFFAAB6C5),fontSize=12.sp)
                    }
                }
            }
        }
    }
}

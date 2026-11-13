package online.jrocai.phone

import android.provider.OpenableColumns
import android.util.Base64
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
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
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import online.jrocai.phone.data.FileClient
import online.jrocai.phone.data.SecureSettings
import org.json.JSONObject

@Composable
fun FileScreen(settings:SecureSettings,client:FileClient,onBack:()->Unit,runOnMain:((()->Unit))->Unit) {
    val context= LocalContext.current
    var files by remember { mutableStateOf(listOf<JSONObject>()) }
    var status by remember { mutableStateOf("Sign in to upload and manage encrypted files.") }
    var busy by remember { mutableStateOf(false) }
    fun refresh() {
        val token=settings.readIdentityToken();val base=settings.readGatewayUrl()
        if(token.isBlank()){status="Sign in on the Account screen first.";return}
        if(busy)return
        busy=true
        Thread {
            val result=runCatching { client.list(base,token) }
            runOnMain { result.onSuccess{data->files=(0 until data.length()).mapNotNull{data.optJSONObject(it)};status="Loaded ${files.size} encrypted files."}.onFailure{status=it.message ?: "File list unavailable."};busy=false }
        }.start()
    }
    val picker=rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if(uri!=null && !busy) {
            val token=settings.readIdentityToken();val base=settings.readGatewayUrl()
            if(token.isBlank())status="Sign in on the Account screen first."
            else {
                busy=true
                Thread {
                    val result=runCatching {
                        val bytes=context.contentResolver.openInputStream(uri)?.use{it.readBytes()} ?: throw IllegalStateException("Unable to read selected file.")
                        if(bytes.isEmpty() || bytes.size>5*1024*1024)throw IllegalArgumentException("Choose a file between 1 byte and 5 MiB.")
                        val name=context.contentResolver.query(uri,arrayOf(OpenableColumns.DISPLAY_NAME),null,null,null)?.use { cursor ->
                            if(cursor.moveToFirst())cursor.getString(0) else null
                        } ?: (uri.lastPathSegment ?: "upload.bin")
                        client.upload(base,token,name,context.contentResolver.getType(uri) ?: "application/octet-stream",Base64.encodeToString(bytes,Base64.NO_WRAP))
                        client.list(base,token)
                    }
                    runOnMain { result.onSuccess{data->files=(0 until data.length()).mapNotNull{data.optJSONObject(it)};status="File encrypted and stored."}.onFailure{status=it.message ?: "Encrypted upload failed."};busy=false }
                }.start()
            }
        }
    }
    Surface(modifier=Modifier.fillMaxSize(),color=Color(0xFF0B0F14)) {
        Column(modifier=Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(18.dp),verticalArrangement=Arrangement.spacedBy(10.dp)) {
            Row(modifier=Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) {
                Column {
                    Text("SECURE FILE MANAGER",color=Color.White,fontSize=20.sp,fontWeight=FontWeight.Bold)
                    Text("Account-owned AES-GCM encrypted files",color=Color(0xFF00B3FF),fontSize=11.sp)
                }
                Button(onClick=onBack){Text("Back")}
            }
            Card(colors=CardDefaults.cardColors(containerColor=Color(0xFF151C25)),modifier=Modifier.fillMaxWidth()) {
                Column(Modifier.padding(14.dp),verticalArrangement=Arrangement.spacedBy(7.dp)) {
                    Text("Files are encrypted by the Environment Agent before storage. The encryption key must be configured in its secret store. Maximum upload size: 5 MiB.",color=Color(0xFFAAB6C5),fontSize=12.sp)
                    Button(enabled=!busy,modifier=Modifier.fillMaxWidth(),onClick={picker.launch(arrayOf("*/*"))}){Text("Choose File and Encrypt")}
                    Button(enabled=!busy,modifier=Modifier.fillMaxWidth(),onClick={refresh()}){Text("Refresh My Files")}
                    Text(status,color=Color(0xFFAAB6C5),fontSize=12.sp)
                }
            }
            files.forEach { file ->
                val id=file.optString("file_id")
                Card(colors=CardDefaults.cardColors(containerColor=Color(0xFF151C25)),modifier=Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(12.dp),verticalArrangement=Arrangement.spacedBy(5.dp)) {
                        Text(file.optString("name"),color=Color.White,fontWeight=FontWeight.Bold)
                        Text(file.optString("content_type")+" • "+file.optLong("size_bytes")+" bytes",color=Color(0xFFAAB6C5),fontSize=11.sp)
                        Button(enabled=!busy,onClick={
                            val token=settings.readIdentityToken();val base=settings.readGatewayUrl()
                            if(!busy){busy=true;Thread{val result=runCatching{client.delete(base,token,id);client.list(base,token)};runOnMain{result.onSuccess{data->files=(0 until data.length()).mapNotNull{data.optJSONObject(it)};status="Encrypted file deleted."}.onFailure{status=it.message ?: "File deletion failed."};busy=false}}.start()}
                        }){Text("Delete File")}
                    }
                }
            }
        }
    }
}

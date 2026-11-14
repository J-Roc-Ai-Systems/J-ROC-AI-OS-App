package online.jrocai.phone

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
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
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import online.jrocai.phone.data.SecureSettings
import online.jrocai.phone.data.WaveElevenFifteenPlatformClient
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun WaveElevenFifteenHub(onBack: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val settings = remember(context) { SecureSettings(context) }
    val client = remember { WaveElevenFifteenPlatformClient() }
    var status by remember { mutableStateOf("Not connected") }
    var collectionStatus by remember { mutableStateOf("Catalogue not loaded") }
    var waves by remember { mutableStateOf(emptyList<Pair<String, List<Pair<Int, String>>>>()) }
    var busy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf("") }

    fun refresh() {
        if (busy) return
        busy = true
        error = ""
        scope.launch {
            try {
                val result = withContext(Dispatchers.IO) {
                    val url = settings.readGatewayUrl()
                    val token = settings.readGatewayToken()
                    Pair(client.load(url, token), client.loadCollections(url, token))
                }
                val waveArray = result.first.optJSONArray("waves")
                val parsed = mutableListOf<Pair<String, List<Pair<Int, String>>>>()
                if (waveArray != null) {
                    for (i in 0 until waveArray.length()) {
                        val item = waveArray.getJSONObject(i)
                        val batches = item.optJSONArray("batches")
                        val batchItems = mutableListOf<Pair<Int, String>>()
                        if (batches != null) for (j in 0 until batches.length()) {
                            val batch = batches.getJSONObject(j)
                            batchItems.add(Pair(batch.optInt("batch"), batch.optString("name")))
                        }
                        parsed.add(Pair(item.optString("name"), batchItems))
                    }
                }
                waves = parsed
                status = "Connected • " + result.first.optInt("batch_count") + " batches registered"
                collectionStatus = result.second.optInt("count").toString() + " typed service collections available"
            } catch (exception: Exception) {
                status = "Connection unavailable"
                error = exception.message ?: "Unable to load the platform catalogue."
            } finally {
                busy = false
            }
        }
    }

    LaunchedEffect(Unit) { refresh() }
    Surface(modifier = Modifier.fillMaxSize(), color = Color(0xFF0B0F14)) {
        Column(
            modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Text("J-ROC AI", color = Color.White, fontSize = 25.sp, fontWeight = FontWeight.Bold)
            Text("WAVES 11–15 • PLATFORM EXPANSION", color = Color(0xFF00B3FF), fontSize = 11.sp, fontWeight = FontWeight.Bold)
            Button(onClick = onBack) { Text("Back to Command Center") }
            Card(colors = CardDefaults.cardColors(containerColor = Color(0xFF142333)), modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(15.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
                    Text("Live platform catalogue", color = Color.White, fontSize = 17.sp, fontWeight = FontWeight.Bold)
                    Text(status, color = Color(0xFFAAB6C5), fontSize = 12.sp)
                    Text(collectionStatus, color = Color(0xFFAAB6C5), fontSize = 12.sp)
                    Button(onClick = { refresh() }, enabled = !busy) { Text(if (busy) "Connecting…" else "Refresh platform catalogue") }
                    if (error.isNotBlank()) Text(error, color = Color(0xFFFFC266), fontSize = 12.sp)
                    Text("The gateway token is read from encrypted device settings and is never displayed.", color = Color(0xFF8F9DAD), fontSize = 11.sp)
                }
            }
            Card(colors = CardDefaults.cardColors(containerColor = Color(0xFF142333)), modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(15.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
                    Text("50 batches • 5 platform waves", color = Color.White, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                    Text("Knowledge and intelligence; productivity and communications; finance and commerce records; creator studio; infrastructure reliability and governance. External actions remain approval-gated and require separately authorized workers.", color = Color(0xFFAAB6C5), fontSize = 12.sp)
                    Text("Zero-dollar spending policy • No payment capture", color = Color(0xFF83CFA6), fontSize = 11.sp, fontWeight = FontWeight.Bold)
                }
            }
            waves.forEachIndexed { index, wave ->
                Text("WAVE " + (index + 11), color = Color(0xFF00B3FF), fontSize = 13.sp, fontWeight = FontWeight.Bold)
                Text(wave.first, color = Color.White, fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
                wave.second.forEach { batch ->
                    Card(colors = CardDefaults.cardColors(containerColor = Color(0xFF151C25)), modifier = Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            Text("BATCH " + batch.first, color = Color(0xFF00B3FF), fontSize = 10.sp, fontWeight = FontWeight.Bold)
                            Text(batch.second, color = Color.White, fontSize = 14.sp, fontWeight = FontWeight.SemiBold)
                            Text("Typed service collection and authenticated API foundation", color = Color(0xFFAAB6C5), fontSize = 11.sp)
                        }
                    }
                }
            }
        }
    }
}

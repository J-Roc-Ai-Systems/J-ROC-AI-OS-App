package online.jrocai.phone

import androidx.compose.foundation.background
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
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private data class WaveModule(val batch: Int, val title: String, val description: String, val status: String = "Not connected")

@Composable
fun WaveTwoHub(onBack: () -> Unit) {
    val modules = listOf(
        WaveModule(11,"Application Factory","Create and organize Android, desktop, web and backend projects."),
        WaveModule(12,"Artificial Intelligence Brain","Coordinate reasoning, memory, models and agents."),
        WaveModule(13,"Integration Engine","Register approved services and protected connection references."),
        WaveModule(14,"Production Worker System","Manage worker registrations, queued jobs and execution history."),
        WaveModule(15,"Device Management","Register supported devices and their authorized capabilities."),
        WaveModule(16,"Platform Integration","Connect internal modules through documented service interfaces."),
        WaveModule(17,"Communication Center","Review system notifications and operational alerts."),
        WaveModule(18,"Knowledge Center","Search approved technical documents and project knowledge."),
        WaveModule(19,"File Management","Manage file metadata, storage references and access policy."),
        WaveModule(20,"Application Management","Maintain the application inventory and release references.")
    )
    Surface(modifier=Modifier.fillMaxSize(), color=Color(0xFF0B0F14)) {
        Column(modifier=Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp), verticalArrangement=Arrangement.spacedBy(12.dp)) {
            Row(modifier=Modifier.fillMaxWidth(), horizontalArrangement=Arrangement.SpaceBetween) {
                Column {
                    Text("J-ROC AI", color=Color.White, fontSize=25.sp, fontWeight=FontWeight.Bold)
                    Text("WAVE 2 • INTELLIGENCE AND PRODUCTION", color=Color(0xFF00B3FF), fontSize=10.sp, fontWeight=FontWeight.Bold)
                }
                Button(onClick=onBack, colors=ButtonDefaults.buttonColors(containerColor=Color(0xFF1B2632))) { Text("Back") }
            }
            Card(colors=CardDefaults.cardColors(containerColor=Color(0xFF142333)), modifier=Modifier.fillMaxWidth()) {
                Column(Modifier.padding(18.dp), verticalArrangement=Arrangement.spacedBy(6.dp)) {
                    Text("Production infrastructure", color=Color(0xFF00B3FF), fontWeight=FontWeight.Bold)
                    Text("Ten connected development areas", color=Color.White, fontSize=20.sp, fontWeight=FontWeight.Bold)
                    Text("Service status is not shown as live until a secured backend connection is configured.", color=Color(0xFFAAB6C5), fontSize=12.sp)
                }
            }
            modules.forEach { module ->
                Card(colors=CardDefaults.cardColors(containerColor=Color(0xFF151C25)), modifier=Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), verticalArrangement=Arrangement.spacedBy(5.dp)) {
                        Text("BATCH ${module.batch}", color=Color(0xFF00B3FF), fontSize=10.sp, fontWeight=FontWeight.Bold)
                        Text(module.title, color=Color.White, fontSize=16.sp, fontWeight=FontWeight.SemiBold)
                        Text(module.description, color=Color(0xFFAAB6C5), fontSize=12.sp)
                        Text(module.status, color=Color(0xFFFFC266), fontSize=11.sp)
                    }
                }
            }
            Spacer(Modifier.height(12.dp))
            Text("J-ROC AI • Local-first platform", color=Color(0xFFAAB6C5), fontSize=11.sp)
        }
    }
}

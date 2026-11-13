package online.jrocai.phone

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private val JrocBlue = Color(0xFF00B3FF)
private val Graphite = Color(0xFF0B0F14)
private val Panel = Color(0xFF151C25)
private val Muted = Color(0xFFAAB6C5)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme(
                colorScheme = darkColorScheme(
                    primary = JrocBlue,
                    background = Graphite,
                    surface = Panel,
                    onPrimary = Graphite,
                    onBackground = Color.White,
                    onSurface = Color.White
                )
            ) {
                JrocHomeScreen()
            }
        }
    }
}

@Composable
private fun JrocHomeScreen() {
    Surface(
        modifier = Modifier.fillMaxSize(),
        color = Graphite
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 22.dp, vertical = 28.dp),
            verticalArrangement = Arrangement.spacedBy(20.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = "J-ROC AI",
                        color = Color.White,
                        fontSize = 27.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = "PERSONAL AI PHONE",
                        color = JrocBlue,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.SemiBold,
                        letterSpacing = 2.sp
                    )
                }
                Text("V0.1.0", color = Muted, fontSize = 12.sp)
            }

            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(24.dp),
                colors = CardDefaults.cardColors(containerColor = Panel)
            ) {
                Column(
                    modifier = Modifier.padding(22.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Text("YOUR AI COMMAND CENTER", color = JrocBlue, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                    Text("What do you want to work on?", color = Color.White, fontSize = 21.sp, fontWeight = FontWeight.Bold)
                    Text(
                        "Your J-ROC AI assistant workspace starts here. Assistant connectivity and model routing will be added as separate secure modules.",
                        color = Muted,
                        fontSize = 14.sp,
                        lineHeight = 21.sp
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Button(
                        onClick = { },
                        modifier = Modifier.fillMaxWidth(),
                        colors = ButtonDefaults.buttonColors(containerColor = JrocBlue),
                        shape = RoundedCornerShape(14.dp)
                    ) {
                        Text("Open AI Assistant", color = Graphite, fontWeight = FontWeight.Bold)
                    }
                }
            }

            Text("PHONE TOOLS", color = Muted, fontSize = 11.sp, fontWeight = FontWeight.Bold, letterSpacing = 2.sp)

            ToolCard("Conversations", "Chat history and saved sessions")
            ToolCard("Device Tools", "Device information and diagnostics")
            ToolCard("Model Center", "Local and connected AI model settings")
            ToolCard("Settings", "Privacy, account, and app preferences")

            Spacer(modifier = Modifier.weight(1f))
            Text(
                "J-ROC AI • Built for your devices",
                modifier = Modifier.align(Alignment.CenterHorizontally),
                color = Muted,
                fontSize = 11.sp
            )
        }
    }
}

@Composable
private fun ToolCard(title: String, description: String) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = Panel)
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 18.dp, vertical = 16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(title, color = Color.White, fontWeight = FontWeight.SemiBold, fontSize = 15.sp)
                Text(description, color = Muted, fontSize = 12.sp)
            }
        }
    }
}

package online.jrocai.phone

import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.weight
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import online.jrocai.phone.data.ChatMessage
import online.jrocai.phone.data.ConversationStore
import online.jrocai.phone.data.EnvGatewayClient
import online.jrocai.phone.data.SecureSettings
import java.text.DateFormat
import java.util.Date

private val JrocBlue = Color(0xFF00B3FF)
private val Graphite = Color(0xFF0B0F14)
private val Panel = Color(0xFF151C25)
private val Muted = Color(0xFFAAB6C5)

private val destinations = listOf(
    "Command Center", "AI Assistant", "J-Bot", "Model Center",
    "Conversations", "Device Tools", "Settings", "Wave 2", "Waves 3–5"
)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val secureSettings = SecureSettings(this)
        val conversationStore = ConversationStore(this)
        val gateway = EnvGatewayClient()
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
                JrocPhoneApp(
                    secureSettings = secureSettings,
                    conversationStore = conversationStore,
                    gateway = gateway,
                    runOnMain = { action -> Handler(Looper.getMainLooper()).post { action() } }
                )
            }
        }
    }
}

@Composable
private fun JrocPhoneApp(
    secureSettings: SecureSettings,
    conversationStore: ConversationStore,
    gateway: EnvGatewayClient,
    runOnMain: ((() -> Unit)) -> Unit
) {
    var selected by remember { mutableStateOf("Command Center") }
    val messages = remember { mutableStateListOf<ChatMessage>().apply { addAll(conversationStore.load()) } }

    Surface(modifier = Modifier.fillMaxSize(), color = Graphite) {
        Column(
            modifier = Modifier.fillMaxSize().padding(top = 22.dp, bottom = 12.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Column(modifier = Modifier.padding(horizontal = 18.dp)) {
                Text("J-ROC AI", color = Color.White, fontSize = 27.sp, fontWeight = FontWeight.Bold)
                Text("PERSONAL AI PHONE  •  V0.2.0", color = JrocBlue, fontSize = 10.sp, letterSpacing = 1.7.sp)
            }
            Row(
                modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()).padding(horizontal = 12.dp),
                horizontalArrangement = Arrangement.spacedBy(7.dp)
            ) {
                destinations.forEach { destination ->
                    FilterChip(
                        selected = selected == destination,
                        onClick = { selected = destination },
                        label = { Text(destination, fontSize = 11.sp) }
                    )
                }
            }
            when (selected) {
                "Command Center" -> CommandCenter(
                    onOpen = { selected = it },
                    gatewayConfigured = secureSettings.readGatewayToken().isNotBlank(),
                    messageCount = messages.size
                )
                "AI Assistant", "J-Bot" -> AssistantScreen(
                    title = if (selected == "J-Bot") "J-Bot Repair Intelligence" else "J-ROC AI Assistant",
                    subtitle = if (selected == "J-Bot") "Device troubleshooting and repair guidance" else "Your personal AI assistant",
                    repairMode = selected == "J-Bot",
                    messages = messages,
                    settings = secureSettings,
                    store = conversationStore,
                    gateway = gateway,
                    runOnMain = runOnMain
                )
                "Model Center" -> ModelCenter(secureSettings, gateway, runOnMain)
                "Conversations" -> ConversationManager(messages, onClear = {
                    conversationStore.clear()
                    messages.clear()
                })
                "Device Tools" -> DeviceTools()
                "Wave 2" -> WaveTwoHub(onBack = { selected = "Command Center" })
                "Waves 3–5" -> WaveThreeToFiveHub(onBack = { selected = "Command Center" })
                "Settings" -> SettingsScreen(secureSettings, onClearHistory = {
                    conversationStore.clear()
                    messages.clear()
                })
            }
        }
    }
}

@Composable
private fun CommandCenter(onOpen: (String) -> Unit, gatewayConfigured: Boolean, messageCount: Int) {
    Column(
        modifier = Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 18.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Card(colors = CardDefaults.cardColors(containerColor = Panel), shape = RoundedCornerShape(24.dp)) {
            Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                Text("PHONE COMMAND CENTER", color = JrocBlue, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                Text("Your AI workspace. One place.", color = Color.White, fontSize = 21.sp, fontWeight = FontWeight.Bold)
                Text("Launch your assistant, troubleshoot devices, manage models and keep conversations together.", color = Muted, fontSize = 13.sp)
                Text(if (gatewayConfigured) "Env Agent access token: configured" else "Env Agent access: setup required", color = if (gatewayConfigured) JrocBlue else Muted, fontSize = 12.sp)
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            MetricCard("SAVED MESSAGES", messageCount.toString(), Modifier.weight(1f))
            MetricCard("DEVICE", Build.MODEL.take(18), Modifier.weight(1f))
        }
        ModuleCard("J-ROC AI Assistant", "Chat with your connected AI assistant.", "Open Assistant") { onOpen("AI Assistant") }
        ModuleCard("J-Bot", "Guided phone, tablet and computer troubleshooting.", "Open J-Bot") { onOpen("J-Bot") }
        ModuleCard("Model Center", "Connect the Env Agent and select an available model.", "Manage Models") { onOpen("Model Center") }
        ModuleCard("Conversations", "Browse and clear locally saved chat history.", "View History") { onOpen("Conversations") }
        ModuleCard("Device Tools", "Review Android version, hardware and build details.", "Inspect Device") { onOpen("Device Tools") }
        ModuleCard("J-ROC AI Settings", "Manage privacy, local credentials and preferences.", "Open Settings") { onOpen("Settings") }
        ModuleCard("Wave 2 Production Platform", "Open the ten intelligence and production infrastructure areas.", "Open Wave 2") { onOpen("Wave 2") }
        ModuleCard("Waves 3–5 Platform", "Agent governance, universal repair operations and enterprise services.", "Open Waves 3–5") { onOpen("Waves 3–5") }
        Text("J-ROC AI • Local-first phone workspace", color = Muted, fontSize = 11.sp, modifier = Modifier.align(Alignment.CenterHorizontally))
    }
}

@Composable
private fun MetricCard(label: String, value: String, modifier: Modifier = Modifier) {
    Card(modifier = modifier, colors = CardDefaults.cardColors(containerColor = Panel)) {
        Column(Modifier.padding(14.dp)) {
            Text(label, color = Muted, fontSize = 9.sp, fontWeight = FontWeight.Bold)
            Text(value, color = Color.White, fontWeight = FontWeight.Bold, fontSize = 15.sp)
        }
    }
}

@Composable
private fun ModuleCard(title: String, description: String, action: String, onClick: () -> Unit) {
    Card(colors = CardDefaults.cardColors(containerColor = Panel), shape = RoundedCornerShape(17.dp)) {
        Column(Modifier.fillMaxWidth().padding(15.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(title, color = Color.White, fontWeight = FontWeight.Bold, fontSize = 15.sp)
            Text(description, color = Muted, fontSize = 12.sp)
            Button(onClick = onClick, modifier = Modifier.fillMaxWidth()) { Text(action) }
        }
    }
}

@Composable
private fun AssistantScreen(
    title: String,
    subtitle: String,
    repairMode: Boolean,
    messages: MutableList<ChatMessage>,
    settings: SecureSettings,
    store: ConversationStore,
    gateway: EnvGatewayClient,
    runOnMain: ((() -> Unit)) -> Unit
) {
    var input by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    var status by remember { mutableStateOf("") }

    Column(Modifier.fillMaxSize().padding(horizontal = 14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(title, color = Color.White, fontSize = 20.sp, fontWeight = FontWeight.Bold)
        Text(subtitle, color = Muted, fontSize = 12.sp)
        if (settings.readGatewayToken().isBlank()) {
            Text("Configure the Env Agent URL and access token in Model Center.", color = JrocBlue, fontSize = 12.sp)
        }
        LazyColumn(
            modifier = Modifier.weight(1f).fillMaxWidth(),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            val relevant = messages.filter { it.role != "system" }
            if (relevant.isEmpty()) {
                item {
                    Card(colors = CardDefaults.cardColors(containerColor = Panel)) {
                        Text(
                            if (repairMode) "Describe the device, model and symptoms. J-Bot will guide you through safe diagnostics."
                            else "Start a conversation with J-ROC AI.",
                            modifier = Modifier.padding(16.dp), color = Muted, fontSize = 13.sp
                        )
                    }
                }
            }
            items(relevant) { message ->
                Card(colors = CardDefaults.cardColors(containerColor = if (message.role == "user") Color(0xFF123047) else Panel)) {
                    Column(Modifier.fillMaxWidth().padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(if (message.role == "user") "YOU" else "J-ROC AI", color = JrocBlue, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                        Text(message.text, color = Color.White, fontSize = 13.sp)
                    }
                }
            }
        }
        if (status.isNotBlank()) Text(status, color = Muted, fontSize = 11.sp)
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(value = input, onValueChange = { input = it }, modifier = Modifier.weight(1f), placeholder = { Text("Type your message…") }, maxLines = 4)
            Button(
                enabled = !busy && input.isNotBlank() && settings.readGatewayToken().isNotBlank(),
                onClick = {
                    val prompt = input.trim()
                    input = ""
                    val userMessage = ChatMessage("user", prompt)
                    messages.add(userMessage)
                    store.append(userMessage)
                    busy = true
                    status = "Sending to J-ROC AI Env Agent…"
                    val baseUrl = settings.readGatewayUrl()
                    val token = settings.readGatewayToken()
                    val model = settings.readModel()
                    Thread {
                        val result = runCatching { gateway.respond(baseUrl, token, model, prompt, repairMode) }
                        runOnMain {
                            result.onSuccess {
                                val reply = ChatMessage("assistant", it)
                                messages.add(reply)
                                store.append(reply)
                                status = ""
                            }.onFailure {
                                status = it.message ?: "Gateway request failed. Check Env Agent settings."
                            }
                            busy = false
                        }
                    }.start()
                }
            ) {
                if (busy) CircularProgressIndicator(modifier = Modifier.height(18.dp), strokeWidth = 2.dp) else Text("Send")
            }
        }
    }
}

@Composable
private fun ModelCenter(settings: SecureSettings, gateway: EnvGatewayClient, runOnMain: ((() -> Unit)) -> Unit) {
    var url by remember { mutableStateOf(settings.readGatewayUrl().takeUnless { it.contains("YOUR-API-HOST") } ?: "") }
    var token by remember { mutableStateOf(settings.readGatewayToken()) }
    var model by remember { mutableStateOf(settings.readModel()) }
    var models by remember { mutableStateOf(emptyList<String>()) }
    var status by remember { mutableStateOf("Provider secrets are managed by the server Env Agent, never by the APK.") }
    var busy by remember { mutableStateOf(false) }

    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text("MODEL CENTER", color = JrocBlue, fontSize = 11.sp, fontWeight = FontWeight.Bold)
        Text("Env Agent connection", color = Color.White, fontSize = 21.sp, fontWeight = FontWeight.Bold)
        Text("Enter your HTTPS Env Agent address and its separate gateway access token. The OpenAI provider key stays on the backend.", color = Muted, fontSize = 12.sp)
        OutlinedTextField(value = url, onValueChange = { url = it }, modifier = Modifier.fillMaxWidth(), label = { Text("Env Agent HTTPS URL") }, singleLine = true)
        OutlinedTextField(value = token, onValueChange = { token = it }, modifier = Modifier.fillMaxWidth(), label = { Text("Gateway access token") }, visualTransformation = PasswordVisualTransformation(), singleLine = true)
        OutlinedTextField(value = model, onValueChange = { model = it }, modifier = Modifier.fillMaxWidth(), label = { Text("Model ID") }, singleLine = true)
        Button(onClick = {
            settings.saveGatewayUrl(url)
            settings.saveGatewayToken(token)
            settings.saveModel(model)
            status = "Gateway settings saved on this device."
        }, modifier = Modifier.fillMaxWidth()) { Text("Save Gateway Settings") }
        Button(enabled = !busy && url.startsWith("https://") && token.isNotBlank(), onClick = {
            settings.saveGatewayUrl(url)
            settings.saveGatewayToken(token)
            busy = true
            status = "Checking Env Agent and loading available models…"
            Thread {
                val result = runCatching { gateway.listModels(url, token) }
                runOnMain {
                    result.onSuccess {
                        models = it
                        status = "Connected. ${it.size} model IDs are available to this gateway."
                    }.onFailure {
                        status = it.message ?: "Connection failed."
                    }
                    busy = false
                }
            }.start()
        }, modifier = Modifier.fillMaxWidth()) { Text(if (busy) "Checking…" else "Test Connection / Load Models") }
        Text(status, color = Muted, fontSize = 12.sp)
        models.take(60).forEach { id ->
            Button(onClick = { model = id; settings.saveModel(id) }, modifier = Modifier.fillMaxWidth()) {
                Text(if (model == id) "Selected: $id" else id)
            }
        }
        Text("OpenAI API billing is separate from ChatGPT subscriptions. Model access depends on the provider account and backend configuration.", color = Muted, fontSize = 11.sp)
    }
}

@Composable
private fun ConversationManager(messages: List<ChatMessage>, onClear: () -> Unit) {
    Column(Modifier.fillMaxSize().padding(horizontal = 18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text("CONVERSATION MANAGER", color = JrocBlue, fontSize = 11.sp, fontWeight = FontWeight.Bold)
        Text("Saved chat history", color = Color.White, fontSize = 21.sp, fontWeight = FontWeight.Bold)
        Text("${messages.size} messages stored locally on this device.", color = Muted, fontSize = 12.sp)
        Button(onClick = onClear, enabled = messages.isNotEmpty(), modifier = Modifier.fillMaxWidth()) { Text("Clear Conversation History") }
        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            items(messages.asReversed()) { message ->
                Card(colors = CardDefaults.cardColors(containerColor = Panel)) {
                    Column(Modifier.fillMaxWidth().padding(12.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
                        Text("${message.role.uppercase()}  •  ${DateFormat.getDateTimeInstance().format(Date(message.timestamp))}", color = JrocBlue, fontSize = 9.sp)
                        Text(message.text, color = Color.White, fontSize = 13.sp)
                    }
                }
            }
        }
    }
}

@Composable
private fun DeviceTools() {
    val rows = listOf(
        "Manufacturer" to Build.MANUFACTURER,
        "Brand" to Build.BRAND,
        "Device" to Build.DEVICE,
        "Model" to Build.MODEL,
        "Product" to Build.PRODUCT,
        "Android version" to Build.VERSION.RELEASE,
        "SDK level" to Build.VERSION.SDK_INT.toString(),
        "Build fingerprint" to Build.FINGERPRINT
    )
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text("DEVICE TOOLS", color = JrocBlue, fontSize = 11.sp, fontWeight = FontWeight.Bold)
        Text("Device diagnostics", color = Color.White, fontSize = 21.sp, fontWeight = FontWeight.Bold)
        Text("Read-only device and operating system information. This screen does not modify the device.", color = Muted, fontSize = 12.sp)
        rows.forEach { (label, value) ->
            Card(colors = CardDefaults.cardColors(containerColor = Panel)) {
                Column(Modifier.fillMaxWidth().padding(13.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(label.uppercase(), color = JrocBlue, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                    Text(value.ifBlank { "Not reported" }, color = Color.White, fontSize = 12.sp)
                }
            }
        }
    }
}

@Composable
private fun SettingsScreen(settings: SecureSettings, onClearHistory: () -> Unit) {
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("J-ROC AI SETTINGS", color = JrocBlue, fontSize = 11.sp, fontWeight = FontWeight.Bold)
        Text("Privacy and customization", color = Color.White, fontSize = 21.sp, fontWeight = FontWeight.Bold)
        Card(colors = CardDefaults.cardColors(containerColor = Panel)) {
            Column(Modifier.padding(15.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text("Account", color = Color.White, fontWeight = FontWeight.Bold)
                Text("Cloud account sign-in and multi-device synchronization are not connected in this build.", color = Muted, fontSize = 12.sp)
                Text("Gateway token: ${if (settings.readGatewayToken().isBlank()) "Not configured" else "Encrypted local storage"}", color = Muted, fontSize = 12.sp)
                Text("Conversation history: Local app storage", color = Muted, fontSize = 12.sp)
                Text("Cloud backup: Disabled", color = Muted, fontSize = 12.sp)
            }
        }
        Button(onClick = { settings.saveGatewayToken("") }, modifier = Modifier.fillMaxWidth()) { Text("Remove Saved Gateway Token") }
        Button(onClick = onClearHistory, modifier = Modifier.fillMaxWidth()) { Text("Delete Local Conversation History") }
        Text("Customization", color = Color.White, fontWeight = FontWeight.Bold)
        Text("J-ROC Blue accent • Graphite dark interface", color = Muted, fontSize = 12.sp)
        Text("Version 0.2.0 • Android application", color = Muted, fontSize = 11.sp)
    }
}

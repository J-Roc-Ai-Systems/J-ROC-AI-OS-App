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
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import online.jrocai.phone.data.IdentityClient
import online.jrocai.phone.data.SecureSettings
import org.json.JSONObject

@Composable
fun AccountScreen(
    settings:SecureSettings,
    client:IdentityClient,
    onBack:()->Unit,
    runOnMain:((()->Unit))->Unit
) {
    var email by remember { mutableStateOf("") }
    var displayName by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var status by remember { mutableStateOf("Sign in or create a J-ROC AI account.") }
    var userLabel by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }

    fun showUser(data:JSONObject) {
        val user=data.optJSONObject("user") ?: data
        userLabel=listOf(user.optString("display_name"),user.optString("email"),"Role: "+user.optString("role"))
            .filter { it.isNotBlank() && !it.endsWith(": ") }.joinToString("\n")
    }
    fun runRequest(request:()->JSONObject, success:(JSONObject)->Unit) {
        if(busy)return
        busy=true
        status="Contacting J-ROC AI Identity..."
        Thread {
            val result=runCatching { request() }
            runOnMain {
                result.onSuccess {
                    success(it)
                    status="Account request completed."
                }.onFailure {
                    status=it.message ?: "Account request failed."
                }
                busy=false
            }
        }.start()
    }
    Surface(modifier=Modifier.fillMaxSize(),color=Color(0xFF0B0F14)) {
        Column(modifier=Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(18.dp),verticalArrangement=Arrangement.spacedBy(12.dp)) {
            Row(modifier=Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween) {
                Column {
                    Text("J-ROC AI ACCOUNT",color=Color.White,fontSize=21.sp,fontWeight=FontWeight.Bold)
                    Text("Secure account session",color=Color(0xFF00B3FF),fontSize=11.sp)
                }
                Button(onClick=onBack){Text("Back")}
            }
            Card(colors=CardDefaults.cardColors(containerColor=Color(0xFF151C25)),modifier=Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp),verticalArrangement=Arrangement.spacedBy(9.dp)) {
                    Text("Account details",color=Color.White,fontWeight=FontWeight.Bold)
                    OutlinedTextField(value=email,onValueChange={email=it},label={Text("Email address")},singleLine=true,modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=displayName,onValueChange={displayName=it},label={Text("Display name (registration)")},singleLine=true,modifier=Modifier.fillMaxWidth())
                    OutlinedTextField(value=password,onValueChange={password=it},label={Text("Password")},visualTransformation=PasswordVisualTransformation(),singleLine=true,modifier=Modifier.fillMaxWidth())
                    Text("New accounts require at least 12 characters. Account recovery and email verification are not yet implemented.",color=Color(0xFFAAB6C5),fontSize=11.sp)
                    Button(enabled=!busy && email.isNotBlank() && password.isNotBlank(),modifier=Modifier.fillMaxWidth(),onClick={
                        val base=settings.readGatewayUrl()
                        val e=email.trim();val p=password
                        runRequest({client.login(base,e,p)}) {
                            settings.saveIdentityToken(it.optString("access_token"))
                            showUser(it)
                            password=""
                        }
                    }){Text("Sign In")}
                    Button(enabled=!busy && email.isNotBlank() && displayName.isNotBlank() && password.length>=12,modifier=Modifier.fillMaxWidth(),onClick={
                        val base=settings.readGatewayUrl()
                        val e=email.trim();val name=displayName.trim();val p=password
                        runRequest({client.register(base,e,name,p)}) {
                            settings.saveIdentityToken(it.optString("access_token"))
                            showUser(it)
                            password=""
                        }
                    }){Text("Create Account")}
                    Button(enabled=!busy,modifier=Modifier.fillMaxWidth(),onClick={
                        val token=settings.readIdentityToken()
                        if(token.isBlank()) status="No saved account session is available."
                        else runRequest({client.me(settings.readGatewayUrl(),token)}) { showUser(it) }
                    }){Text("Check Saved Session")}
                    if(userLabel.isNotBlank()) {
                        Text(userLabel,color=Color(0xFF00B3FF),fontSize=12.sp)
                        Button(enabled=!busy,modifier=Modifier.fillMaxWidth(),onClick={
                            val token=settings.readIdentityToken()
                            runRequest({client.logout(settings.readGatewayUrl(),token)}) {
                                settings.clearIdentityToken()
                                userLabel=""
                                status="Signed out. The local session token was cleared."
                            }
                        }){Text("Sign Out")}
                    }
                    Text(status,color=Color(0xFFAAB6C5),fontSize=12.sp)
                }
            }
        }
    }
}

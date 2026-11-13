package online.jrocai.phone.data

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** Stores only the user's gateway access token locally. Provider keys remain server-side. */
class SecureSettings(context: Context) {
    private val prefs = context.getSharedPreferences("jrocai_secure_settings", Context.MODE_PRIVATE)
    private val alias = "jrocai_gateway_token_key"

    fun saveGatewayToken(value: String) = saveEncrypted("gateway_token", value)
    fun readGatewayToken(): String = readEncrypted("gateway_token")
    fun saveIdentityToken(value: String) = saveEncrypted("identity_session_token", value)
    fun readIdentityToken(): String = readEncrypted("identity_session_token")
    fun clearIdentityToken() = saveEncrypted("identity_session_token", "")

    fun saveGatewayUrl(value: String) {
        prefs.edit().putString("gateway_url", value.trim().trimEnd('/')).apply()
    }
    fun readGatewayUrl(): String = prefs.getString("gateway_url", "https://YOUR-API-HOST.example.com") ?: ""

    fun saveModel(model: String) {
        prefs.edit().putString("model", model.trim()).apply()
    }
    fun readModel(): String = prefs.getString("model", "gpt-4.1-mini") ?: "gpt-4.1-mini"

    private fun saveEncrypted(name: String, value: String) {
        if (value.isBlank()) {
            prefs.edit().remove(name).apply()
            return
        }
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, getOrCreateKey())
        val encrypted = cipher.doFinal(value.toByteArray(Charsets.UTF_8))
        prefs.edit().putString(name, Base64.encodeToString(cipher.iv + encrypted, Base64.NO_WRAP)).apply()
    }

    private fun readEncrypted(name: String): String {
        val packed = prefs.getString(name, null) ?: return ""
        return try {
            val bytes = Base64.decode(packed, Base64.NO_WRAP)
            val cipher = Cipher.getInstance("AES/GCM/NoPadding")
            cipher.init(
                Cipher.DECRYPT_MODE,
                getOrCreateKey(),
                GCMParameterSpec(128, bytes.copyOfRange(0, 12))
            )
            String(cipher.doFinal(bytes.copyOfRange(12, bytes.size)), Charsets.UTF_8)
        } catch (_: Exception) {
            ""
        }
    }

    private fun getOrCreateKey(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey(alias, null) as? SecretKey)?.let { return it }
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        generator.init(
            KeyGenParameterSpec.Builder(
                alias,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
            ).setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setRandomizedEncryptionRequired(true)
                .build()
        )
        return generator.generateKey()
    }
}

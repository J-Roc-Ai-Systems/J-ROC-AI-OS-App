package online.jrocai.sdk

data class AgentTask(
    val taskId: String,
    val agentId: String,
    val taskType: String,
    val status: String,
    val requiresApproval: Boolean,
    val createdAt: String?
)

data class SdkResult<T>(val value: T? = null, val error: SdkError? = null)
data class SdkError(val code: String, val message: String, val httpStatus: Int? = null)
fun interface SdkCallback<T> { fun onComplete(result: SdkResult<T>) }
fun interface AccessTokenProvider {
    /** Supply a short-lived authenticated session token, never a model-provider key. */
    fun getAccessToken(): String?
}

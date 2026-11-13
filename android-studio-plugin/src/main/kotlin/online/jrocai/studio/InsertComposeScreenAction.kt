package online.jrocai.studio

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.command.WriteCommandAction
import com.intellij.openapi.editor.Editor
import com.intellij.openapi.fileEditor.FileEditorManager
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.Messages

class InsertComposeScreenAction : AnAction() {
    override fun actionPerformed(event: AnActionEvent) {
        val project = event.project ?: return
        val editor = FileEditorManager.getInstance(project).selectedTextEditor
        if (editor == null) {
            Messages.showInfoMessage(
                project,
                "Open a Kotlin source file and place the caret where the screen should be inserted.",
                "J-ROC AI Compose Template"
            )
            return
        }

        val template = composeScreenTemplate()
        insertAtCaret(project, editor, template)
    }

    private fun insertAtCaret(project: Project, editor: Editor, template: String) {
        WriteCommandAction.runWriteCommandAction(project) {
            val document = editor.document
            document.insertString(editor.caretModel.offset, template)
            editor.caretModel.moveToOffset(editor.caretModel.offset + template.length)
        }
    }

    private fun composeScreenTemplate(): String = """

@Composable
fun NewJRocAiScreen(
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .background(Color(0xFF0B0F14))
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text(
            text = "J-ROC AI",
            color = Color(0xFF00B3FF),
            style = MaterialTheme.typography.headlineMedium
        )
        Text(
            text = "New screen",
            color = Color.White,
            style = MaterialTheme.typography.bodyLarge
        )
    }
}
""".trimIndent()
}

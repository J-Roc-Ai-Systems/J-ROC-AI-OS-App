package online.jrocai.studio

import com.intellij.openapi.project.Project
import com.intellij.openapi.wm.ToolWindow
import com.intellij.openapi.wm.ToolWindowFactory
import com.intellij.ui.components.JBLabel
import com.intellij.ui.components.JBPanel
import com.intellij.ui.components.JBScrollPane
import com.intellij.util.ui.JBUI
import java.awt.BorderLayout
import java.awt.Font
import javax.swing.JButton
import javax.swing.JPanel
import javax.swing.JTextArea

class JRocAiToolWindowFactory : ToolWindowFactory {
    override fun createToolWindowContent(project: Project, toolWindow: ToolWindow) {
        val panel = JBPanel<JBPanel<*>>(BorderLayout()).apply {
            border = JBUI.Borders.empty(14)
        }

        val heading = JBLabel("J-ROC AI Developer Tools").apply {
            font = font.deriveFont(Font.BOLD, 18f)
        }

        val guidance = JTextArea(
            """
            Welcome to the J-ROC AI Android workspace.

            Project workflow
            1. Open the app module and edit Kotlin / Jetpack Compose screens.
            2. Sync Gradle after changing build configuration.
            3. Run the app configuration on an emulator or connected device.
            4. Review Build Output and Logcat before committing changes.

            Available starter action
            Right-click inside a Kotlin editor and choose:
            Insert J-ROC Compose Screen

            Security
            Never place provider API keys in source code, resources, Gradle files,
            or the APK. Use an authenticated backend for provider credentials.
            """.trimIndent()
        ).apply {
            isEditable = false
            lineWrap = true
            wrapStyleWord = true
            background = panel.background
            border = JBUI.Borders.emptyTop(12)
        }

        val footer = JBLabel("J-ROC Blue  •  Local-first  •  Secure by design")

        panel.add(heading, BorderLayout.NORTH)
        panel.add(JBScrollPane(guidance), BorderLayout.CENTER)
        panel.add(footer, BorderLayout.SOUTH)

        val content = com.intellij.ui.content.ContentFactory.getInstance()
            .createContent(panel, "", false)
        toolWindow.contentManager.addContent(content)
    }
}

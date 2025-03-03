import EnigmatrixUI
import sys

# Run the UI
app = EnigmatrixUI.QApplication(sys.argv)
app.setStyle("Fusion")
window = EnigmatrixUI.EnigmatrixApp()
window.show()
sys.exit(app.exec())
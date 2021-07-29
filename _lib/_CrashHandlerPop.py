import sys, os
from PyQt5.QtWidgets import QMessageBox, QApplication

class ErrorWindow(QMessageBox):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Application Crashed')
        message = ('An error occurred and the application was terminated.\n\n'
                   'A log was created at:\n' + os.getcwd() + '\crash.log.')
        self.setText(message)
        self.setIcon(QMessageBox.Critical)
        self.show()

def main():
    app = QApplication(sys.argv)
    ex = ErrorWindow()
    sys.exit(app.exec_())

main()
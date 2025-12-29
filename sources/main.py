import sys
from PyQt5.QtWidgets import QApplication
from modules.gui import LiveGraphApp
from PyQt5.QtGui import QIcon


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("assets//pepe-the-frog.ico"))
    window = LiveGraphApp()
    print("Application started with Python executable:", sys.executable)
    window.show()
    app.exec_()


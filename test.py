import sys

from PySide6.QtCore import QLibraryInfo, qVersion
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget


class MyWidget(QWidget):
    pass


class Window(QMainWindow):
    def __init__(self):
        super().__init__()


if __name__ == "__main__":
    print("Python {}.{}".format(sys.version_info[0], sys.version_info[1]))
    print(QLibraryInfo.build())
    app = QApplication(sys.argv)
    window = Window()
    window.setWindowTitle(qVersion())
    window.show()
    sys.exit(app.exec())

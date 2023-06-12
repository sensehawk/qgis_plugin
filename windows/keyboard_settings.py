from qgis.PyQt import QtWidgets
from PyQt5 import QtGui


class ShortcutSettings(QtWidgets.QWidget):
    def __init__(self, project):
        super().__init__()
        self.layout = QtWidgets.QVBoxLayout(self)
        self.project = project
        self.shortcuts_table = QtWidgets.QTableWidget(self)
        self.load_current_settings()
        self.save_button = QtWidgets.QPushButton(self)
        self.save_button.setText("Save")
        self.layout.addWidget(self.save_button)
        self.save_button.clicked.connect(self.save_new_shortcuts)

    def load_current_settings(self):
        self.shortcuts_table.setRowCount(len(self.project.feature_shortcuts))
        self.shortcuts_table.setColumnCount(2)
        self.shortcuts_table.verticalHeader().setVisible(False)
        self.shortcuts_table.horizontalHeader().setVisible(False)

        i = 0
        for k, v in self.project.feature_shortcuts.items():
            feature_type_item = QtWidgets.QTableWidgetItem(v)
            feature_type_item.setBackground(QtGui.QColor(self.project.color_code[v]))
            self.shortcuts_table.setItem(i, 0, feature_type_item)
            self.shortcuts_table.setItem(i, 1, QtWidgets.QTableWidgetItem(str(k)))
            i += 1
        self.layout.addWidget(self.shortcuts_table)

    def save_new_shortcuts(self):
        new_shortcuts = {}
        for row in range(self.shortcuts_table.rowCount()):
            feature_type = self.shortcuts_table.item(row, 0).text()
            shortcut = self.shortcuts_table.item(row, 1).text()
            new_shortcuts[shortcut] = feature_type
        self.project.feature_shortcuts = new_shortcuts
        self.hide()
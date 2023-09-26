from PyQt5 import QtWidgets
from qgis.PyQt.QtCore import Qt
from functools import partial

class GroupsForm:
    def __init__(self, groups_dict, group_selection_layout, workspace_window):
        self.groups_groupbox = QtWidgets.QGroupBox('Groups:')
        self.myform = QtWidgets.QFormLayout()
        for group_uid, group_obj in groups_dict.items():
            group_button = QtWidgets.QPushButton(f'{group_obj.name}')
            group_button.clicked.connect(partial(workspace_window.load_group_window, group_uid))
            self.myform.addRow(group_button)
            if group_obj.container:
                print("From groups homepage")
                print(group_obj.name)
                print(group_obj.container.applications)

        self.create_new_button = QtWidgets.QPushButton('+')
        self.myform.addRow(self.create_new_button)
        self.groups_groupbox.setLayout(self.myform) 

        self.scroll_widget = QtWidgets.QScrollArea()
        self.scroll_widget.setWidget(self.groups_groupbox)
        self.scroll_widget.setWidgetResizable(True)
        self.scroll_widget.setFixedHeight(400)
        # Replace the scroll widget if it exists
        if workspace_window.groups_form:
            group_selection_layout.replaceWidget(workspace_window.groups_form.scroll_widget, self.scroll_widget)
        else:
            group_selection_layout.addWidget(self.scroll_widget, 0, Qt.AlignTop)

class GroupSelectionWidget(QtWidgets.QWidget):
    def __init__(self, workspace_window):
        super().__init__()
        group_selection_layout = QtWidgets.QVBoxLayout(self)
        workspace_window.group_selection_layout = group_selection_layout
        workspace_window.groups_form = GroupsForm(workspace_window.home_window.groups_dict, group_selection_layout, workspace_window)
        workspace_window.pm_workspace_grid.addWidget(self, 0, 1, Qt.AlignTop)
        workspace_window.dock_widget.setFixedSize(520, 830)
        #TODO: Use grid layout instead of VBOX layout
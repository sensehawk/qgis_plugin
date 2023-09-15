from PyQt5 import QtWidgets


class ProjectManagementWindow(QtWidgets.QWidget):
    def __init__(self, org_uid, iface):
        super().__init__()
        self.iface = iface
        self.org_uid = self.asset_selection_window.org_uid
        self.asset_uid = self.asset_selection_window.asset_uid
        self.user_email = self.asset_selection_window.user_email
        self.core_token = self.asset_selection_window.core_token
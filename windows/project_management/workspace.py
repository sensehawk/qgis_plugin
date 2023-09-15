from PyQt5 import QtWidgets
from project_management import ProjectManagementWindow
from ...utils import container_details, group_details

class WorkspaceWindow(QtWidgets.QWidget):
    def __init__(self, home_window, iface):
        super().__init__()
        self.iface = iface
        self.org_uid = home_window.org_uid
        self.asset_uid = home_window.asset_uid
        self.user_email = home_window.user_email
        self.core_token = home_window.core_token
        self.home_window = home_window
    
    def get_all_details(self):
        self.containers_dict = container_details(self.asset_uid, self.org_uid, self.core_token)
        self.groups_dict = group_details(self.asset_uid, self.org_uid, self.core_token) # list of all groups in asset and there respective projects 
        self.projects_list = {"Group A": [], "Group B": []}
        pass



    
    def init_project_management(self):


    
        
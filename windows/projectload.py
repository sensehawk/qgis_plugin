from qgis.PyQt.QtCore import Qt
from PyQt5 import QtCore, QtGui, QtWidgets 
from qgis.core import Qgis, QgsApplication, QgsTask, QgsProject, QgsMessageLog
from ..tasks import loadTask
from PyQt5.QtWidgets import QLineEdit, QCompleter, QVBoxLayout, QPushButton, QComboBox
from PyQt5.QtCore import QRect
from ..utils import download_file, load_vectors, categorize_layer , group_details, combobox_modifier

class SimpleLoadWindow(QtWidgets.QWidget):
    def __init__(self, homeobj, iface):
        super().__init__()
        self.iface = iface
        self.home = homeobj
        self.core_token = self.home.core_token
        self.asset_uid = self.home.asset_uid
        self.org_uid = self.home.org_uid
        # self.iface.addDockWidget(Qt.LeftDockWidgetArea, self)
        mygroupbox = QtWidgets.QGroupBox('Project details')
        myform = QtWidgets.QFormLayout()
        labellist = []
        combolist = []
        val = 5   
        for i in range(val):
            labellist.append(QtWidgets.QLabel('project name'))
            button = QtWidgets.QPushButton('P'*i)
            button.clickecd.connect(self.project)
            combolist.append(button)

            myform.addRow(labellist[i],combolist[i])
        # scroll.setGeometry(70,60,301,101)
        mygroupbox.setLayout(myform)

        self.group_details = group_details(self.asset_uid, self.org_uid, self.core_token)
        group_list = list(self.group_details.keys())
        self.group_combobox = QComboBox(self) 
        self.group = combobox_modifier(self.group_combobox, group_list)
        # self.group.currentIndexChanged.connect(self.group_tree)
        # group_combobox.setGeometry(70,20,300,25)
        self.back_button = QPushButton(self)
        # back_button.setGeometry(10,150,31,21)
        self.back_button.setText('home')
        self.back_button.clicked.connect(self.back_to_home)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidget(mygroupbox)
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(200)
        # scroll.setGeometry(70,60,301,101)

        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(scroll)
        self.layout.addWidget(self.group)
        self.layout.addWidget(self.back_button)
        # layout.geometry((0,0),(413*255))
        self.layout.setGeometry(QRect(500, 400, 400, 200))

    def project(self):
        pass

    def group_tree(self):
        mygroupbox = QtWidgets.QGroupBox('Project details')
        myform = QtWidgets.QFormLayout()
        labellist = []
        combolist = []
        val = 10    
        for i in range(val):
            labellist.append(QtWidgets.QLabel('project name'))
            combolist.append(QtWidgets.QPushButton('P'*i))
            myform.addRow(labellist[i],combolist[i])
        # scroll.setGeometry(70,60,301,101)
        mygroupbox.setLayout(myform)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidget(mygroupbox)
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(200)
        self.layout.addWidget(scroll)
        # scroll.setGeometry(70,60,301,101)

    def back_to_home(self):
        self.home.show()
        self.hide()
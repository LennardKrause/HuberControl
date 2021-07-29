import logging
from PyQt5 import QtCore, QtWidgets, QtGui

'''
 todo:
 - add curser selection
'''

class Browser(QtWidgets.QWidget):
    pBsig_selectedItem = QtCore.pyqtSignal(str)
 
    def __init__(self, aList, aTitle, chIconName, addIconName, keyword):
        QtWidgets.QWidget.__init__(self)
        self.log = logging.getLogger('HuberControl.' + __name__)
        self.log.debug(aTitle)
        self.title = aTitle
        self.left = 100
        self.top = 100
        self.width = 480
        self.height = 240
        self.projects = aList
        self.keyword = keyword
        self.addIconName = addIconName
        self.autoSelected = None
        self.currentItem = None
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(':/icons/{}.png'.format(chIconName)), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setWindowIcon(icon)
        # call 'self.windowFlags()' to make sure the
        # window is active after changing the flag
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.WindowCloseButtonHint)
        # dont show [x] in upper right corner when previousItem is None
        if not self.currentItem:
            self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.WindowTitleHint)
        self.initUI()
    
    def initUI(self):
        self.log.debug('Called')
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)

        # Box
        self.dataGroupBox = QtWidgets.QGroupBox('{}: {}'.format(self.keyword, self.currentItem))
        self.projectView = QtWidgets.QTreeView()
        self.projectView.setSortingEnabled(True)
        self.projectView.setRootIsDecorated(False)
        self.projectView.setAlternatingRowColors(True)
        self.projectView.setExpandsOnDoubleClick(False)
        self.projectView.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.projectView.header().setStretchLastSection(True)
        self.projectView.header().setCascadingSectionResizes(True)
        self.projectView.header().setDefaultSectionSize(140)
        self.projectView.doubleClicked.connect(self.entryDoubleClicked)
        self.projectView.setToolTip('Double click to accept.')
        
        dataLayout = QtWidgets.QHBoxLayout()
        dataLayout.addWidget(self.projectView)
        self.dataGroupBox.setLayout(dataLayout)
        
        # Button
        # if self.addIconName is None the button will not be added to the layout
        self.btn_addUser = QtWidgets.QToolButton()        
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(':/icons/{}.png'.format(self.addIconName)), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.btn_addUser.setIconSize(QtCore.QSize(50, 30))
        self.btn_addUser.setIcon(icon)
        self.btn_addUser.setToolTip('Click to add a new {}.'.format(self.keyword))
        self.btn_addUser.clicked.connect(self.addNewAndSelect)

        model = self.createProjectView(self)
        self.projectView.setModel(model)
        # add projects to the view, if any
        if len(self.projects) > 0:
            for entry in self.projects:
                proj, edited, created = entry
                self.addProject(model, proj, edited, created)
            # sort by date
            self.projectView.sortByColumn(1, QtCore.Qt.DescendingOrder)
            # auto select the first entry
            self.autoSelected = self.autoSelectEntry(0, model)
            self.projectView.selectionModel().selectionChanged.connect(self.onSelectionChanged)
        
        mainLayout = QtWidgets.QVBoxLayout()
        mainLayout.addWidget(self.dataGroupBox)
        if self.addIconName:
            mainLayout.addWidget(self.btn_addUser, 0, QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter)
        self.setLayout(mainLayout)
        # put the focus on this window
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.show()
    
    def createProjectView(self, parent):
        self.log.debug('Called')
        model = QtGui.QStandardItemModel(0, 3, parent)
        model.setHeaderData(0, QtCore.Qt.Horizontal, self.keyword)
        model.setHeaderData(1, QtCore.Qt.Horizontal, 'Edited')
        model.setHeaderData(2, QtCore.Qt.Horizontal, 'Created')
        return model

    def addProject(self, model, Project, Edited, Created):
        self.log.debug(Project)
        model.insertRow(0)
        model.setData(model.index(0, 0), Project)
        model.setData(model.index(0, 1), Edited)
        model.setData(model.index(0, 2), Created)
    
    def onSelectionChanged(self, selected, deselected):
        indexes = selected.indexes()
        if indexes:
            index = indexes[0]
            self.autoSelected = index.model().itemData(index)[0]
            self.log.debug(self.autoSelected)
    
    def autoSelectEntry(self, idx, model):
        self.log.debug(idx)
        # auto select the first entry
        self.projectView.setCurrentIndex(model.index(idx, 0))
        return model.itemData(self.projectView.selectedIndexes()[0])[idx]

    def entryDoubleClicked(self, index):
        self.log.debug(index.row())
        self.currentItem = self.projectView.selectedIndexes()[0].model().index(index.row(), 0).data()
        self.close()

    def keyPressEvent(self, event):
        self.log.debug('Called')
        '''
         - First entry is selected when initialized
         - If empty, call addNew
        '''
        if event.key() in [QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter]:
            if self.autoSelected:
                self.currentItem = self.autoSelected
                self.close()
            else:
                self.addNewAndSelect()
    
    def addNew(self):
        self.log.debug('Called')
        aName, okPressed = QtWidgets.QInputDialog.getText(self, 'Add New {}:'.format(self.keyword),
                                                                'Enter {}name:'.format(self.keyword),
                                                                text=self.autoSelected,
                                                                flags = (QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.WindowTitleHint))
        if okPressed:
            model = self.createProjectView(self)
            self.projectView.setModel(model)
            self.addProject(model, aName, '-', '-')
            for entry in self.projects:
                proj, edited, created = entry
                self.addProject(model, proj, edited, created)
            # sort by date
            self.projectView.sortByColumn(1, QtCore.Qt.AscendingOrder)
            # auto select the first entry
            self.autoSelected = self.autoSelectEntry(0, model)
        else:
            # auto select the first entry
            self.autoSelected = self.currentItem
    
    def addNewAndSelect(self):
        self.log.debug('Called')
        self.addNew()
        self.currentItem = self.autoSelected
        self.close()
    
    def closeEvent(self, event):
        self.log.debug('Called')
        self.pBsig_selectedItem.emit(self.currentItem)
        event.accept()

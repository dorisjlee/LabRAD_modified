from PyQt4 import QtGui, QtCore, uic
from qtui.QCustomSpinBox import QCustomSpinBox
from twisted.internet.defer import inlineCallbacks, returnValue
from common.okfpgaservers.dacserver.DacConfiguration import hardwareConfiguration as hc

UpdateTime = 100 # ms
SIGNALID = 270836
SIGNALID2 = 270835

class MultipoleControl(QtGui.QWidget):
    def __init__(self, reactor, cxn=None):
        super(MultipoleControl, self).__init__()
        self.cxn = cxn
        self.updating_gui = False
        self.reactor = reactor
        self.connect()        

    @inlineCallbacks    
    def makeGUI(self):
        self.multipoles = yield self.dac_server.get_multipole_names()
        shuttle_on, current_Cfile, Cfile_list = yield self.dac_server.get_cfile_info() # add to server

        self.controls = {k: QCustomSpinBox(k, (-20.,20.)) for k in self.multipoles}
        self.load_button = QtGui.QPushButton('Load')
        self.shuttle_button = QtGui.QPushButton('Shuttle')
        self.Cfile_menu = QtGui.QComboBox()
        self.Cfile_menu.insertItem(0, current_Cfile)
        self.Cfile_menu.insertSeparator(1)
        self.Cfile_menu.insertItems(2, Cfile_list)

        for k in self.multipoles:
            self.layout.addWidget(self.controls[k])        
        if shuttle_on:
            self.layout.addWidget(self.load_button)
            self.layout.addWidget(self.shuttle_button)
        self.layout.addWidget(self.Cfile_menu)

        self.inputUpdated = False
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.sendToServer)
        self.timer.start(UpdateTime)   

        for k in self.multipoles:
            self.controls[k].onNewValues.connect(self.inputHasUpdated)
        self.Cfile_menu.currentIndexChanged.connect(self.CfileSelected)
        self.load_button.released.connect(self.loadButtonPressed)
        self.shuttle_button.released.connect(self.shuttleButtonPressed)

        self.setLayout(self.layout)
        yield self.followSignal(0, 0)	
        
    @inlineCallbacks
    def connect(self):
        from labrad.wrappers import connectAsync
        from labrad.types import Error
        if not self.cxn:
            cxn = yield connectAsync()
        self.dac_server = yield cxn.dac_server_dev
        yield self.setupListeners()
        self.layout = QtGui.QVBoxLayout()
        self.makeGUI()        
        
    def inputHasUpdated(self):
        if self.updating_gui: return
        self.inputUpdated = True
        self.multipole_values = {m: round(self.controls[m].spinLevel.value(), 3) for m in self.multipoles}
        
    def sendToServer(self):
        if self.updating_gui: return
        if self.inputUpdated:
            self.dac_server.set_multipole_values(self.multipole_values.items())
            self.inputUpdated = False
    
    @inlineCallbacks
    def CfileSelected(self, c):
        self.updating_gui = True
        yield self.dac_server.set_control_file(str(self.Cfile_menu.currentText()))
        self.updating_gui = False
        yield self.updateGUI(None, None)
        

    @inlineCallbacks
    def updateGUI(self, c, ID):
        self.updating_gui = True
        for i in range(self.layout.count()): 
            self.layout.itemAt(i).widget().close()
        self.controls = None
        
        yield self.makeGUI()
        self.inputHasUpdated()
        self.updating_gui = False

    @inlineCallbacks
    def loadButtonPressed(self):
        yield self.dac_server.load()

    @inlineCallbacks
    def shuttleButtonPressed(self):
        yield self.dac_server.shuttle()

    @inlineCallbacks    
    def setupListeners(self):
        yield self.dac_server.signal__ports_updated(SIGNALID)
        yield self.dac_server.addListener(listener=self.followSignal, source=None, ID=SIGNALID) 
        # yield self.dac_server.signal__cfile_updated(SIGNALID)
        # yield self.dac_server.addListener(listener=self.updateGUI, source=None, ID=SIGNALID)
        
    @inlineCallbacks
    def followSignal(self, x, s):
        multipoles = yield self.dac_server.get_multipole_values()
        # set current QComboBox item
        for (k,v) in multipoles:
            self.controls[k].setValueNoSignal(v)          

    def closeEvent(self, x):
        self.reactor.stop()  

class ChannelControl (QtGui.QWidget):
    def __init__(self, reactor, cxn=None):
        super(ChannelControl, self).__init__()
        self.cxn = cxn
        self.reactor = reactor
        self.makeGUI()
        self.connect()
     
    def makeGUI(self):
        layout = QtGui.QGridLayout()
        self.controls = {k: QCustomSpinBox(k, hc.dac_dict[k].allowedVoltageRange) for k in hc.dac_dict.keys()}
        if bool(hc.sma_dict):
            sma_box = QtGui.QGroupBox('SMA Out')
            sma_layout = QtGui.QVBoxLayout()
            sma_box.setLayout(sma_layout)
        elecBox = QtGui.QGroupBox('Electrodes')
        elec_layout = QtGui.QGridLayout()
        elecBox.setLayout(elec_layout)
        if bool(hc.sma_dict):
            layout.addWidget(sma_box, 0, 0)
        layout.addWidget(elecBox, 0, 1)

        for s in hc.sma_dict:
            sma_layout.addWidget(self.controls[s], alignment = QtCore.Qt.AlignRight)
        elec_list = hc.elec_dict.keys()
        elec_list.sort()
        if bool(hc.center_electrode):
            elec_list.pop(hc.center_electrode-1)
        for i,e in enumerate(elec_list):
            if int(e) <= len(elec_list)/2:
                elec_layout.addWidget(self.controls[e], len(elec_list)/2 - int(i), 0)
            elif int(e) > len(elec_list)/2:
                elec_layout.addWidget(self.controls[e], len(elec_list) - int(i), 2)
        if bool(hc.center_electrode):
            self.controls[str(hc.center_electrode).zfill(2)].title.setText('CNT')
            elec_layout.addWidget(self.controls[str(hc.center_electrode).zfill(2)], len(elec_list)/2, 1) 

        spacer = QtGui.QSpacerItem(20,40,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.MinimumExpanding)
        if bool(hc.sma_dict):
            sma_layout.addItem(spacer)        
        self.inputUpdated = False                
        self.timer = QtCore.QTimer(self)        
        self.timer.timeout.connect(self.sendToServer)
        self.timer.start(UpdateTime)
        
        for k in hc.dac_dict.keys():
            self.controls[k].onNewValues.connect(self.inputHasUpdated(k))

        layout.setColumnStretch(1, 1)                   
        self.setLayout(layout)

    @inlineCallbacks
    def connect(self):
        from labrad.wrappers import connectAsync
        from labrad.types import Error
        if self.cxn is None:
            self.cxn = yield connectAsync()
        self.dac_server = yield self.cxn.dac_server_dev
        yield self.setupListeners()
        yield self.followSignal(0, 0)

    def inputHasUpdated(self, name):
        def iu():
            self.inputUpdated = True
            self.changedChannel = name
        return iu

    def sendToServer(self):
        if self.inputUpdated:            
            self.dac_server.set_individual_analog_voltages([(self.changedChannel, round(self.controls[self.changedChannel].spinLevel.value(), 3))]*17)
            self.inputUpdated = False
            
    @inlineCallbacks    
    def setupListeners(self):
        yield self.dac_server.signal__ports_updated(SIGNALID2)
        yield self.dac_server.addListener(listener=self.followSignal, source=None, ID=SIGNALID2)
    
    @inlineCallbacks
    def followSignal(self, x, s):
        av = yield self.dac_server.get_analog_voltages()
        for (c, v) in av:
            self.controls[c].setValueNoSignal(v)

    def closeEvent(self, x):
        self.reactor.stop()        

class ChannelMonitor(QtGui.QWidget):
    def __init__(self, reactor, cxn=None):
        super(ChannelMonitor, self).__init__()
        self.cxn = cxn
        self.reactor = reactor        
        self.makeGUI()
        self.connect()
        
    def makeGUI(self):      
        self.displays = {k: QtGui.QLCDNumber() for k in hc.dac_dict.keys()}               
        layout = QtGui.QGridLayout()
        if bool(hc.sma_dict):        
            sma_box = QtGui.QGroupBox('SMA Out')
            sma_layout = QtGui.QGridLayout()
            sma_box.setLayout(sma_layout)       
        elecBox = QtGui.QGroupBox('Electrodes')
        elec_layout = QtGui.QGridLayout()
        elec_layout.setColumnStretch(1, 2)
        elec_layout.setColumnStretch(3, 2)
        elec_layout.setColumnStretch(5, 2)
        elecBox.setLayout(elec_layout)
        if bool(hc.sma_dict):
            layout.addWidget(sma_box, 0, 0)
        layout.addWidget(elecBox, 0, 1)
        
        if bool(hc.sma_dict):
            for k in hc.sma_dict:
                self.displays[k].setAutoFillBackground(True)
                sma_layout.addWidget(QtGui.QLabel(k), hc.dac_dict[k].smaOutNumber, 0)
                sma_layout.addWidget(self.displays[k], hc.dac_dict[k].smaOutNumber, 1)
                s = hc.sma_dict[k].smaOutNumber+1

        elec_list = hc.elec_dict.keys()
        elec_list.sort()
        if bool(hc.center_electrode):
            elec_list.pop(hc.center_electrode-1)
        for i,e in enumerate(elec_list):
            if bool(hc.sma_dict):            
                self.displays[k].setAutoFillBackground(True)
            if int(i) < len(elec_list)/2:
                elec_layout.addWidget(QtGui.QLabel(e), len(elec_list)/2 - int(i), 0)
                elec_layout.addWidget(self.displays[e], len(elec_list)/2 - int(i), 1)
            else:
                elec_layout.addWidget(QtGui.QLabel(e), len(elec_list) - int(i), 4)
                elec_layout.addWidget(self.displays[e], len(elec_list) - int(i), 5)
        if bool(hc.center_electrode):
            elec_layout.addWidget(QtGui.QLabel('CNT'), len(elec_list)/2 + 1, 2)
            elec_layout.addWidget(self.displays[str(hc.center_electrode).zfill(2)], len(elec_list)/2 + 1, 3)      
          
        if bool(hc.sma_dict):
            spacer = QtGui.QSpacerItem(20,40,QtGui.QSizePolicy.Minimum,QtGui.QSizePolicy.MinimumExpanding)
            sma_layout.addItem(spacer, s, 0,10, 2)  

        self.setLayout(layout)  
                
    @inlineCallbacks
    def connect(self):
        from labrad.wrappers import connectAsync
        from labrad.types import Error
        if self.cxn is None:
            self.cxn = yield connectAsync()
        self.dac_server = yield self.cxn.dac_server_dev
        yield self.setupListeners()
        yield self.followSignal(0, 0)       
        
    @inlineCallbacks    
    def setupListeners(self):
        yield self.dac_server.signal__ports_updated(SIGNALID2)
        yield self.dac_server.addListener(listener=self.followSignal, source=None, ID=SIGNALID2)
    
    @inlineCallbacks
    def followSignal(self, x, s):
        av = yield self.dac_server.get_analog_voltages()
        grayscale = 210
        sensitivity = 255 - grayscale           
        for (k, v) in av:
            self.displays[k].display(float(v)) 
            if abs(v) > 30:
                self.displays[k].setStyleSheet("QWidget {background-color: orange }")
            else:
                R = int(grayscale + v*sensitivity/30.)
                G = int(grayscale - abs(v*sensitivity/30.))
                B = int(grayscale - v*sensitivity/30.)
                hexclr = '#%02x%02x%02x' % (R, G, B)
                self.displays[k].setStyleSheet("QWidget {background-color: "+hexclr+" }")

    def closeEvent(self, x):
        self.reactor.stop()

class DAC_Control(QtGui.QMainWindow):
    def __init__(self, reactor, cxn=None):
        super(DAC_Control, self).__init__()
        self.cxn = cxn
        self.reactor = reactor

        channel_control_tab = self.buildChannelControlTab()        
        multipole_control_tab = self.buildMultipoleControlTab()
        tab = QtGui.QTabWidget()
        tab.addTab(multipole_control_tab,'&Multipoles')
        tab.addTab(channel_control_tab, '&Channels')
        self.setWindowTitle('DAC Control')
        self.setCentralWidget(tab)
    
    def buildMultipoleControlTab(self):
        widget = QtGui.QWidget()
        layout = QtGui.QGridLayout()
        layout.addWidget(ChannelMonitor(self.reactor, self.cxn),0,0)
        layout.addWidget(MultipoleControl(self.reactor, self.cxn),0,1)
        widget.setLayout(layout)
        return widget

    def buildChannelControlTab(self):
        widget = QtGui.QWidget()
        layout = QtGui.QGridLayout()
        layout.addWidget(ChannelControl(self.reactor, self.cxn),0,0)
        widget.setLayout(layout)
        return widget
         
    def closeEvent(self, x):
        self.reactor.stop()  

if __name__ == "__main__":
    a = QtGui.QApplication( [] )
    import qt4reactor
    qt4reactor.install()
    from twisted.internet import reactor
    DAC_Control = DAC_Control(reactor)
    DAC_Control.show()
    reactor.run()

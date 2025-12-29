import time
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QLabel, QLineEdit
)
import pyqtgraph as pg
from pyqtgraph.exporters import CSVExporter
from pandas import read_csv, DataFrame
from modules.watcher import FolderWatcher
import numpy as np
import os
from modules.processing import SpectrumProcessor
import shutil


class LiveGraphApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.watcher = None
        self.yData = []
        self.yFittedData = []#
        self.yOffset =[]
        self.yFitOffset = []
        self.xTime = []
        self.xCutTime = []
        self.offsetMode = False
        self.offset = None
        
        self.folder = None
        self.allow_update = True
        self.initialTimeSec = None
        self.lastFrameTimeSec = 0.0  # Default durationMin, can be updated based on yData

        self.sections = []
        self.activeSection = None
        self.startMode = True
        self.captureMode = False

        self.region = []
        self.rate = 0.1  # Default rate, can be updated based on yData
        self.initUI()
        
    # --------------------------------------------------

    def initUI(self):
        self.setWindowTitle("Real-Time Analysis")
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout()
        self.button_Layout = QHBoxLayout()
        self.entries_Layout = QHBoxLayout()

        self.central_widget.setLayout(self.layout)
        
        self.btn_folder = QPushButton("Select Folder",self)
        self.btn_save = QPushButton("Save",self)
        self.btn_fit = QPushButton("Fit",self)
        self.btn_Configure = QPushButton("Configure",self)
        self.btn_Select =QPushButton("Select",self)
        self.btn_clear_section =QPushButton("Clear",self)
        self.btn_frame_save =QPushButton("Save Frame",self)
        self.btn_Offset_Mode =QPushButton("Offset Mode",self)
        self.btn_OffsetCal =QPushButton("Cal Base",self)



        self.btn_folder.setFixedSize(100,40)
        self.btn_Configure.setFixedSize(70,40)
        self.btn_save.setFixedSize(55,40)
        self.btn_fit.setFixedSize(50,40)
        self.btn_Select.setFixedSize(70,40)
        self.btn_clear_section.setFixedSize(70,40)
        self.btn_frame_save.setFixedSize(110,40)
        self.btn_Offset_Mode.setFixedSize(100,40)

        self.value_Label = QLabel("Value : ")
        self.fitted_value = QLabel("Fitted Value : ................... ")

        self.input_Field = QLineEdit()
        self.input_Field.setPlaceholderText("initial guess (optional)")
        self.input_Frame = QLineEdit()
        self.input_Frame.setPlaceholderText("Frame Numbers")
        
        self.button_Layout.addWidget(self.btn_folder)
        self.button_Layout.addWidget(self.btn_save)
        self.button_Layout.addWidget(self.btn_fit)
        self.button_Layout.addWidget(self.btn_Configure)
        self.button_Layout.addWidget(self.value_Label)
        self.button_Layout.addWidget(self.input_Field)
        self.button_Layout.addWidget(self.btn_Select)
        self.button_Layout.addWidget(self.btn_clear_section)
        self.button_Layout.addWidget(self.fitted_value)
        self.button_Layout.addWidget(self.btn_frame_save)
        self.button_Layout.addWidget(self.input_Frame)
        self.button_Layout.addWidget(self.btn_Offset_Mode)
        self.button_Layout.addWidget(self.btn_OffsetCal)


        self.layout.addLayout(self.button_Layout)
        self.layout.setContentsMargins(10,40,10,10)

        # self.label_rates = QLabel("Rates: ---")
        # self.layout.addWidget(self.label_rates)

        # Graph area
        self.plot_widget = pg.PlotWidget()
        exporter = CSVExporter(self.plot_widget.plotItem)
   
        # exporter.export("outputPlot.csv")
        self.vb = self.plot_widget.getViewBox() #plotitem.vb
        self.plot_widget.setLabel('left','Wavelength (nm)')
        self.plot_widget.setLabel('bottom','Time (seconds)')
        self.plot_widget.setTitle('Real-Time Graph',color='w')
        self.plot_curve = self.plot_widget.plot([], [], pen='w')
        self.plot_fitted = self.plot_widget.plot([], [], pen='r')
        #self.plot_raw = self.plot_widget.plot([], [], pen='g')
        # self.curve = self.plot_widget.plot([], [], pen='y')
        self.layout.addWidget(self.plot_widget)

        self.btn_folder.clicked.connect(self.select_folder)
        self.btn_save.clicked.connect(self.save)
        self.btn_fit.clicked.connect(self.section_fit)
        self.btn_Configure.clicked.connect(self.configure)
        self.btn_Select.clicked.connect(self.add_section_or_stop)
        self.btn_clear_section.clicked.connect(self.clear_section)
        self.btn_frame_save.clicked.connect(self.copySelectedFiles)
        self.btn_Offset_Mode.clicked.connect(self.turnOffsetMode) 
        self.btn_OffsetCal.clicked.connect(self.calBaseline)  
        
        #self.setLayout(self.layout) # Testing
        self.setWindowTitle("Real-time Graph")
        self.setGeometry(200,200,1300,700)

        self.timer = pg.QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(500)

    # # --------------------------------------------------
    # def createFolders(self):
        
    #     result_folder_path = os.path.join(self.folder,"Result")
    #     os.makedirs(result_folder_path,exist_ok=True)
    #     corrected_folder_path = os.path.join(self.folder,"Corrected Data")
    #     os.makedirs(corrected_folder_path,exist_ok=True)

    def select_folder(self):
        f = QFileDialog.getExistingDirectory(self, "Select Folder")
        if not f:
            return

        self.folder = f
        if self.watcher:
            self.watcher.stop()
        
        self.watcher = FolderWatcher(f)
        self.watcher.new_data.connect(self.triggerSignal)
        
        self.watcher.start()
        
        if os.path.isfile(os.path.join(self.folder,"Result","MinList.csv")):
            df = read_csv(os.path.join(self.folder,"Result","MinList.csv"))
            self.yData=df["Min Wavelengths"].to_list()
            self.xTime=df["Time"].to_list()
            self.plot_curve.setData(self.xTime, self.yData)
        else:
            print("Not Found")

    def configure(self):
        SpectrumProcessor.initParams[0]= float(self.input_Field.text())
      
    def save(self):
        if not self.folder:
            return
        length = len(self.yData)
        durationMin = (self.lastFrameTimeSec-self.initialTimeSec)/60
        self.xTime = np.linspace(0,durationMin,length).tolist()
        df = DataFrame({"Time": self.xTime, "Min Wavelengths": self.yData})
        
        file_location = os.path.join(self.folder,"Result")
        os.makedirs(file_location,exist_ok=True)#removable
        df.to_csv(os.path.join(file_location,"MinList.csv") , index=False)

    def saveFittedData(self,fx,fy,name):
        if not self.folder:
            return
        
        file_location = os.path.join(self.folder,"Result","FittedData"+name+".csv")
        df = DataFrame({"Time": fx, "Fitted Wavelengths": fy})
        df.to_csv(file_location , index=False)

    def triggerSignal(self, v,index,df):
        self.yData.append(v)
        self.lastFrameTimeSec = time.time() 
        if self.initialTimeSec == None:
            self.initialTimeSec = self.lastFrameTimeSec
        self.xTime.append((self.lastFrameTimeSec-self.initialTimeSec)/60)

        if self.offset is not None:
            self.yOffset.append(v - self.offset)

        self.save_corrected(index,df)

    def save_corrected(self,index,df):
        
        if not self.folder:
            return
        file_location = os.path.join(self.folder,"Corrected Data")
        os.makedirs(file_location,exist_ok=True)
        df.to_csv(os.path.join(file_location,"Frame"+str(int(index)).zfill(4)+".csv") , index=False)

    def update_plot(self):
        if self.allow_update and self.offsetMode == False:
            self.plot_curve.setData(self.xTime, self.yData) # X is still len and not time
        elif( self.allow_update and self.offsetMode == True):
            self.plot_curve.setData(self.xTime, self.yOffset)

    def calBaseline(self):
        if len(self.sections)==1:

            # myList = [x for x in self.xTime if (self.sections[0][0]< x <self.sections[0][1])]
            x1= np.array(self.xTime).searchsorted(self.sections[0][0],side='right')
            x2= np.array(self.xTime).searchsorted(self.sections[0][1],side='right')
            myList = self.yData[x1:x2]
            self.offset = sum(myList)/len(myList) if myList else None
            print("Cal offset : ",self.offset)

    def section_fit(self):
        if not self.folder:
            return

        df = read_csv(self.folder + "//Result//MinList.csv")
        
        fx,fy, rates= self.watcher.proc.all_section_fit(df,self.sections)

        self.allow_update = False
        self.yFittedData = fy
        self.xCutTime = fx
        m =  None

        if self.watcher.proc.Offset is None:
            if self.offset is not None:
                m = self.offset  
        else:
            m = self.watcher.proc.Offset
            self.offset = m   
        self.yFitOffset = [d - m for d in fy]
        
        if(not self.offsetMode):
            self.plot_fitted.setData(fx, fy)
            self.saveFittedData(fx,fy,"__")
        elif( m is not None):
            self.plot_fitted.setData(fx, self.yFitOffset)
        if m is not None:
            self.saveFittedData(fx, self.yFitOffset,"Offset")

        self.fitted_value.setText("Rates: " + ", ".join([f"{r:.4f}" for r in rates]))
        self.saveRates(rates)

    def saveRates(self,rates):
        myDict = {"Rates":rates}
        df = DataFrame(myDict)
        
        file_location = os.path.join(self.folder,"Result")
        os.makedirs(file_location,exist_ok=True)#removable
        df.to_csv(os.path.join(file_location,"Rates.csv") , index=False)

    def add_section_or_stop(self):
        if not self.captureMode:
            self.plot_widget.scene().sigMouseClicked.connect(self.on_clicked)
            self.captureMode = True
            print("Capture mode ON.")
        else:
            self.plot_widget.scene().sigMouseClicked.disconnect(self.on_clicked)
            self.captureMode = False
            print("Capture mode OFF.")

    def copySelectedFiles(self):
        sourceDir = os.path.join(self.folder, "Corrected Data")
        destDir = os.path.join(self.folder,"Selected Files")
        os.makedirs(destDir, exist_ok=True)
        frames = []
        
        timeF = [float(x) for x in self.input_Frame.text().split(",") ]
        print("Frames to copy at times (s):", timeF)
        if os.path.isfile(os.path.join(self.folder,"Result","MinList.csv")):
            min_file = read_csv(os.path.join(self.folder,"Result","MinList.csv"))
            for i in timeF:
                pos = min_file["Time"].to_numpy().searchsorted(i,side='right')
                frames.append(pos)

            if not frames:
                print("No valid frames savedfound for the given times.")
                return
        else:
            print("No MinList.csv found in Result folder.")
            return
        
        for i in frames:
            temp="Frame"+str(i).zfill(4) + ".csv"
            tempSource_path = os.path.join(sourceDir,temp)
            tempDest_path = os.path.join(destDir,temp)
            print( "Copying:", tempSource_path, " to ", tempDest_path)
            if os.path.isfile(tempSource_path):
                shutil.copy(tempSource_path, tempDest_path)

    def turnOffsetMode(self):
        if self.offsetMode == False:
            if len(self.yData) ==0:
                print("No yData to set offset.")
                return
            if self.watcher.proc.Offset is None:
                if self.offset is None:
                    return
                else:
                    m = self.offset
            else:
                m = self.watcher.proc.Offset
                self.offset = m
            
            self.yOffset = [d - m for d in self.yData]
            
            self.offsetMode = True
            self.plot_curve.setData(self.xTime, self.yOffset)
            self.plot_fitted.setData(self.xCutTime,self.yFitOffset)
            
            print("Offset mode ON. Offset set to:", self.offset)
        else:
            self.offsetMode = False
            
            self.plot_curve.setData(self.xTime, self.yData)
            self.plot_fitted.setData(self.xCutTime,self.yFittedData)
            print("Offset mode OFF.")

    # handles yData to sections[] on clicks
    def on_clicked(self,event):
        if event.button() == pg.QtCore.Qt.LeftButton:
            pos=event.scenePos() #.mapSceneToView(event.scenePos()).x()
            if self.plot_widget.sceneBoundingRect().contains(pos):

                mousePoint = self.vb.mapSceneToView(pos)
                x = (mousePoint.x())
                print("Clicked at x =", x)
                  
                if self.startMode:
                    self.activeSection =[]
                    self.activeSection.append(x)
                    self.startMode=False
                else:
                    self.activeSection.append(x)
                    self.startMode=True
                    self.sections.append(self.activeSection)
                    print("Current Sections:",self.sections)
                    #next add code to visually mark the section on the plot
                    self.region.append(pg.LinearRegionItem(self.activeSection,brush=(100, 100, 150, 50),movable=False))
                    self.plot_widget.addItem(self.region[-1])
                    

        return
    
    def clear_section(self):

        if self.startMode == False:
            self.activeSection=[]
            self.startMode=True
            print("Current Sections cut:",self.sections)
            return
        else:
            if self.sections==[]:
                print("No sections to remove")
                return
            self.sections.pop()
            #remove color/marking of last section on plot
            self.plot_widget.removeItem(self.region[-1])
            self.region.pop()
            print("Current Sections removed:",self.sections)

    def closeEvent(self, e):

        if self.watcher:
            self.watcher.stop()
        e.accept()

import time
from PyQt5.QtCore import QThread, pyqtSignal
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pandas import read_csv,DataFrame
from modules.processing import SpectrumProcessor


class FolderWatcher(QThread):
    new_data = pyqtSignal(float,int,object)

    def __init__(self, folder):
        self.index = 0
        super().__init__()
        self.folder = folder
        self.proc = SpectrumProcessor(folder)#?????
        self.obs = Observer()
        self.run_flag = True
        
    def run(self):
        h = FileHandler(self.new_data,self.proc)
        self.obs.schedule(h, self.folder, recursive=False)
        self.obs.start()
        try:
            while self.run_flag:
                time.sleep(1)
        finally:
            self.obs.stop()
            self.obs.join()

    def stop(self):
        self.run_flag = False
        self.obs.stop()


class FileHandler(FileSystemEventHandler):
    def __init__(self,signal,p):
        self.p = p
        self.signal = signal
        self.ready = False
        self.index=int(0)
        super().__init__()
          
    def on_created(self, event):
        if event.is_directory:
            return

        time.sleep(0.5)
        df = read_csv(event.src_path)
        df = self.p.correct(df)
        

        if not self.ready:
            self.ready = True

        if not self.p.init_params[0]: # better condition // combination
            idx = self.p.find_min(df)
            SpectrumProcessor.init_params[0] = idx
    
        c, _ = self.p.fit_peak(df)
        self.index+=1
        self.signal.emit(c,self.index,df)
        


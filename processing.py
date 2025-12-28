# processing.py
import numpy as np
from pandas import read_csv, DataFrame
from lmfit.models import GaussianModel, ConstantModel
from scipy.signal import savgol_filter
from scipy.optimize import curve_fit


class SpectrumProcessor:
    init_params = [None, -0.7, 20, 1.02]
    Offset = None
    def __init__(self, folder):

        ref = read_csv(folder + "\\SPR.csv")
        self.dark = ref["Dark Data"].to_numpy()
        self.ref = ref["Reference Data"].to_numpy()
        self.n = len(self.ref)

        self.minRawWaves = []
        self.minRawFlux = []
        self.correctedData = []
        self.minWaves = []
        self.minFlux = []   
        self.p0 = [0.01,0] # initial params for section fitting

        self.Offset = None

    # Calculation Parts

    def correct(self, df):
        incident = self.ref - self.dark
        emergent = df["Intensities"].to_numpy() - self.dark

        corr = emergent / incident

        df1 = df.copy()
        df1["Refractives"] = corr
        df1["Emergent"] = emergent
        return df1

    

    def find_min(self, df):
        m = (df["Wavelength (nm)"] >= 550) & (df["Wavelength (nm)"] <= 800)
        idx = df[m]["Refractives"].idxmin()
        self.minRawWaves.append(df["Wavelength (nm)"].iloc[idx])
        self.minRawFlux.append(df["Refractives"].iloc[idx])
        return df["Wavelength (nm)"].iloc[idx]

  

    def fit_peak(self, df, wrange=25):
        x0 = SpectrumProcessor.init_params[0]

        lo = x0 - wrange
        hi = x0 + wrange

        m = (df["Wavelength (nm)"] >= lo) & (df["Wavelength (nm)"] <= hi)
        x = df[m]["Wavelength (nm)"]
        y = df[m]["Refractives"]

        model = GaussianModel() + ConstantModel()
        p = model.make_params()

        p["center"].set(value=x0, min=500, max=850)
        p["amplitude"].set(value = self.init_params[1], max = -0.1)
        p["sigma"].set(value=self.init_params[2],vary=True)
        p['c'].set(value = self.init_params[3], vary = True)
        
        res = model.fit(y, p, x=x)
        best = res.best_fit

        center = res.params["center"].value
        centerIdx = np.argmax(best)
        height = best[centerIdx]

        SpectrumProcessor.init_params = [
            res.params["center"].value,
            res.params["amplitude"].value,
            res.params["sigma"].value,
            res.params["c"].value,
        ]
        self.minWaves.append(center)
        self.minFlux.append(height)

        return center, height
   
    # SECTION FITTING 

    def _select_points(self, y, span=100):
        filtered = savgol_filter(y, 20, 2)# window size 101, polynomial order 2

        x1 = filtered[:-span]
        x2 = filtered[span:]
        diff = x2 - x1
        print("Max Diff:", diff.max())
        boolDiff = ( diff < -5)|( diff > 5 ) #need to account for noise
        flatPoints = [0]
        prev = boolDiff[0]
        sectionPointsId=[0]

        for i in range(len(boolDiff)):
            if boolDiff[i] != prev:
                flatPoints.append(i + span)
            prev = boolDiff[i]

        for i in range(2,len(flatPoints),2):
            temp = flatPoints[i]-flatPoints[i-1]
            temp = temp * 7/8
            index = int(flatPoints[i] + temp)
            sectionPointsId.append(index)

        sectionPointsId[-1]= len(diff)+ span
        print("Section Points:", sectionPointsId)

        return sectionPointsId

        # sectionPointsId.append(len(boolDiff))
        # return sectionPointsId
   

    # exponential piecewise fit
    def fit_this_part(self, x, y):
        
        def fn(x, A, B, C, d):
            return np.where(x <= d, A - B, A - B * np.exp(-C * (x - d)))

        
        p0 = [ y[-1], (y[-1]-y[0]), 0.0025,0.0015]#self.p0[0], self.p0[1]]# b is now positive,
        popt, _ = curve_fit(fn, x, y, p0) # self.p0 = [popt[2],popt[3]]  # update initial params for next fit

        if self.Offset is None:
           
            self.Offset = popt[0]-popt[1]
            
            print("... Offset set to:", self.Offset)

        print("Initial Params:", p0)
        print("Fitted Params:", popt)
        return x,fn(x, *popt), popt[2]

    # public call
    def all_section_fit(self, arr, segmentsT=[]):
        segmentsF = []
        if not segmentsT:

            sectionPointsId = self._select_points(arr["Min Wavelengths"].to_numpy())
            for i in range(len(sectionPointsId) - 1):
                segmentsF.append([sectionPointsId[i], sectionPointsId[i + 1]])
            print(" SegmentsF:",segmentsF,)

        else:
            for i in segmentsT:
                x1 = arr["Time"].to_numpy().searchsorted(i[0],side='right')
                x2 = arr["Time"].to_numpy().searchsorted(i[1],side='right')
                segmentsF.append([x1,x2])
                print("test ", i)
            
        all_y = []
        all_x=[]
        all_rates = []

        for i in segmentsF:
            xCut = arr["Time"][i[0]:i[1]].to_numpy()
            yCut = arr["Min Wavelengths"][i[0]:i[1]].to_numpy()
            
            fx,fy, rate = self.fit_this_part(xCut, yCut)
            all_y.extend(fy)
            all_x.extend(fx)
            all_rates.append(rate)
            

        return all_x, all_y, all_rates # np.yay??
    
if __name__ == "__main__":
    folder = "C:\\Users\\91961\\Desktop\\Jupyter 1\\Spectra Analyser\\Software\\Real Time Analysis\\18-08-2025\\18-08-2025_Ag_50nm_bulk"
    p = SpectrumProcessor(folder)
    ref = read_csv(folder + "\\Result\\MinList.csv")
    y = ref["Min Wavelengths"]
    import matplotlib.pyplot as plt
   
    fx,fy, rates = p.all_section_fit(ref)
    plt.plot(fx,fy, label="Section Fit Data",color='black')

    filtered = savgol_filter(ref["Min Wavelengths"], 100, 2)# window size 101, polynomial order 2
    plt.plot(ref["Time"],ref["Min Wavelengths"], label="Original Data", alpha=0.5   )
    plt.show()
    span = 100
    x1 = filtered[:-span]
    x2 = filtered[span:]
    diff = x2 - x1
    plt.plot(fx[span:], diff, label="dif Data")
    plt.show()


    

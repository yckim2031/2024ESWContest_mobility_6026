import numpy as np
from scipy.signal import cheby2, filtfilt
from scipy.fftpack import fft, fftfreq
import math
import matplotlib.pyplot as plt

class Al_detect:
    def __init__(self, ppg_red, ppg_ir, sampling_rate=256):
        self.ppg_red = ppg_red
        self.ppg_ir = ppg_ir
        self.sampling_rate = sampling_rate

    # Chebyshev2 (0.5Hz ~ 10Hz)
    def apply_chebyshev_filter(self, data, lowcut=0.5, highcut=10, order=3):
        nyquist = 0.5 * self.sampling_rate
        low = lowcut / nyquist
        high = highcut / nyquist
        b, a = cheby2(order, 20, [low, high], btype='bandpass', analog=False)
        filtered_data = filtfilt(b, a, data)
        return filtered_data

    # FFT
    def plot_fft(self):
        filtered_data = self.apply_chebyshev_filter(self.ppg_red, lowcut=0.2, highcut=4)
        filtered_data = -filtered_data

        n = len(filtered_data)
        ppg_fft = fft(filtered_data)
        freq = fftfreq(n, d=1.0/self.sampling_rate)
        fft_magnitude = np.abs(ppg_fft)

        def find_peak_in_band(freq, fft_magnitude, low, high):
            mask = (freq >= low) & (freq <= high)
            if np.any(mask):
                peak_idx = np.argmax(fft_magnitude[mask])
                peak_freq = freq[mask][peak_idx]
                peak_magnitude = fft_magnitude[mask][peak_idx]
                return peak_freq, peak_magnitude
            return None, None

        peaks_3 = []
        bands = [(0.2, 0.5), (0.8, 1.8), (1.8, 4)]
        for low, high in bands:
            peak_freq, peak_magnitude = find_peak_in_band(freq, fft_magnitude, low, high)
            if peak_freq is not None:
                print(f"{low}Hz ~ {high}Hz : {peak_freq:.2f} Hz, magnitude : {peak_magnitude:.2f}")
            else:
                print(f"{low}Hz ~ {high}Hz's peak cannot be found.")
            peaks_3.append(peak_magnitude)
            
        #mask = freq > 0
        #mask &= freq <=4
        
        #plt.plot(freq[mask], fft_magnitude[mask])
        #plt.show()
        return peaks_3, filtered_data

    # SpO2
    def calculate_spo2(self):
        #self.ppg_ir = self.apply_chebyshev_filter(self.ppg_ir,0.5,10)
        #self.ppg_red = self.apply_chebyshev_filter(self.ppg_red,0.5,10)
        dc_ir = np.mean(self.ppg_ir)
        dc_red = np.mean(self.ppg_red)
        ac_ir = np.sqrt(np.mean(np.square(self.ppg_ir - dc_ir)))
        ac_red = np.sqrt(np.mean(np.square(self.ppg_red - dc_red)))
        ror = (ac_red / dc_red) / (ac_ir / dc_ir)
        spo2 = 110 - 25 * ror
        return spo2

    # RSpb, RSbs
    def calculate_RS(self, peaks_3, spo2):
        rspb = peaks_3[1] / (math.sqrt(peaks_3[2]) * math.sqrt(peaks_3[0]) * (spo2 ** 6))
        rsbs = (math.sqrt(peaks_3[1]) * math.sqrt(peaks_3[0])) / (peaks_3[2] * (spo2 ** 6))
        return rspb, rsbs

import time
import threading
import numpy as np
import ADS1x15
import matplotlib.pyplot as plt
from scipy.signal import cheby1, filtfilt, butter
import argparse
import sys

def butter_bandpass(lowcut=0.5, highcut=35, fs=250, order=5):
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(order, [low, high], btype='band')
    return b, a

# Apply the filter to the signal
def apply_filter(data, lowcut=0.5, highcut=35, fs=250, order=4):
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    y = filtfilt(b, a, data)
    return y

def design_chebyshev_bandpass():
    lowcut = 0.8
    highcut = 40
    ripple = 0.5
    order = 4
    nyquist = 0.5 * 250
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = cheby1(order, ripple, [low, high], btype='band')
    return b, a


def adc_configure(adc):
    adc.setGain(adc.PGA_4_096V)
    print(adc.PGA_4_096V)
    adc.setMode(0)
    adc.setDataRate(adc.DR_ADS111X_860) # set 250Hz as the sampling rate
    adc.requestADC(0)
    print("configuration completed")
    return

# Read ADC function
def read_adc(adc, adc_data_list, stop_event):
    sample_interval = 0.004  # Sample every 4 ms
    while not stop_event.is_set():
        start_time = time.perf_counter()
        
        value = adc.getValue()  # Replace with your channel and gain
        if value > 32767:
             value -= 65536
            
        adc_data_list.append(value)
        if len(adc_data_list) > 2500:
            adc_data_list.pop(0)
        elapsed_time = time.perf_counter() - start_time
        time_to_sleep = sample_interval - elapsed_time
        if time_to_sleep > 0:
            time.sleep(time_to_sleep)

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--time', type=int, help='Type time to acquire (sec)')
    args = parser.parse_args()
    return args

def main():
    args = parse_args()
    adc_data_list = []  # Shared list for ADC data
    stop_event = threading.Event()

    adc = ADS1x15.ADS1115(7, address=0x48)
    adc_configure(adc)

    # Start the ADC reading thread
    adc_thread = threading.Thread(target=read_adc, args=(adc, adc_data_list, stop_event))
    adc_thread.start()

    flg = True
    print("Acquisition started")
    time.sleep(20)
    start_time_1 = time.perf_counter()
    while flg:
        if len(adc_data_list) >= 250*10:
            stop_event.set()  # Stop the ADC thread
            adc_thread.join()  # Wait for the thread to finish
            flg = False

    elapsed_time = time.perf_counter() - start_time_1

    print(f"Acquisition complete..., took {elapsed_time} second")

    b, a = design_chebyshev_bandpass()
    filtered_ecg = apply_filter(adc_data_list)
    plt.plot(filtered_ecg)
    plt.show()

if __name__ == "__main__":
    main()
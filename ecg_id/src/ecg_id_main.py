import time
import threading
import numpy as np
import ADS1x15
import matplotlib.pyplot as plt
from scipy.signal import cheby1, filtfilt, butter
import sys
import ecg_prep
import os
import utils
import tensorflow as tf
import model_loader
from sklearn.metrics import accuracy_score

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


def butter_bandpass(lowcut=0.5, highcut=35, fs=250, order=5):
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(order, [low, high], btype='band')
    return b, a

# Apply the filter to the signal
def apply_filter(data, lowcut=0.5, highcut=35, fs=250, order=5):
    b, a = butter_bandpass(lowcut, highcut, fs, order=order)
    y = filtfilt(b, a, data)
    return y


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


def build_dirs(proj_dir):
    template_data_dir = os.path.join(proj_dir, "data", "template")
    save_data_dir = os.path.join(proj_dir, "data", f"processed")
    model_path = os.path.join(proj_dir, "model", "ecg_id_model.h5")
    return {"template_data_dir": template_data_dir, "save_data_dir": save_data_dir, "model_path": model_path}


def create_template(ecg_frames_array, dir_dict):
    template_pulse = np.mean(ecg_frames_array[:20], axis=0)
    template_path_list = utils.path_finder(dir_dict['template_data_dir'], '.npz')
    new_template_name = len(template_path_list) + 1
    new_template_path = os.path.join(dir_dict['template_data_dir'], f"{new_template_name}.npz")
    np.savez(new_template_path, data = template_pulse, raw_data = ecg_frames_array)


def save_data(dir_dict, final_ecg_sigs_array):
    subject_id = data_path.split('/')[-2]
    file_name = f"{subject_id}.npz"
    save_path = os.path.join(dir_dict['save_data_dir'], subject_id, file_name)
    utils.make_save_dir(os.path.split(save_path)[0])
    np.savez(save_path, data=final_ecg_sigs_array)

def calculate_result(y_prob, threshold):
    y_prob_mean = np.mean(y_prob)
    likely = 0
    if y_prob_mean < threshold:
        likely = 0
    else:
        likely = 1
    return likely
    

def verification():
    dir_dict = build_dirs("/home/jhhan/Downloads/ESW_UI/ecg_id/")
    filter_params = {'lowcut':0.8, 'highcut':40, 'ripple':0.5, 'order':4}
    ecg_preprocessor = ecg_prep.ECGPreprocessor(filter_params = filter_params, dir_dict=dir_dict)
    template_data_list = utils.path_finder(dir_dict['template_data_dir'], '.npz')

    b, a = design_chebyshev_bandpass()

    temp_ecg = []
    ecg_repo = []
    flg = True

    adc_data_list = []  # Shared list for ADC data
    stop_event = threading.Event()

    adc = ADS1x15.ADS1115(7, address=0x48)
    adc_configure(adc)

    # Start the ADC reading thread
    adc_thread = threading.Thread(target=read_adc, args=(adc, adc_data_list, stop_event))
    adc_thread.start()

    # Checking Registered Data
    print(f"There is {len(template_data_list)} subjects are saved in the database")
    time.sleep(5)
    print("If you want to register, please press 'r' button, or 'v' to verify")
    mode = ""

    # ================================Keyboard input=====================================
    while True:
        user_input = input("Enter the mode: ")
        if user_input.lower() == 'r':
            required_data_cnt = 20
            mode = "Register"
            print("Executing register mode")
            break
        elif user_input.lower() == 'v':
            required_data_cnt = 5
            mode = "Verification"
            print("Executing verification mode")
            break
        print(f"You entered: {user_input}")

    print(f"{mode} mode is selected. Put your hands on the steering wheel")
    time.sleep(5)
    print("Acquisition started, Keep your hands on the steering wheel.")
    time.sleep(20)
    # start_time_1 = time.perf_counter()
    # elapsed_time = time.perf_counter() - start_time_1

    # ================================Data Acquisition=====================================
    processed_sigs = np.empty((0,200))
    while flg:
        raw_sig = adc_data_list
        if len(raw_sig) >= 2500:
            filtered_ecg = apply_filter(raw_sig)
            new_processed_sig = ecg_preprocessor.process(filtered_ecg, dir_dict, filter_params)
            if new_processed_sig.shape[0] > 0:
                new_processed_sig = np.reshape(new_processed_sig, (-1,200))
                processed_sigs = np.concatenate((processed_sigs, new_processed_sig), axis=0)
                if len(processed_sigs) > required_data_cnt:
                    print("ECG signal collected")
                    flg = False
                    stop_event.set()  # Stop the ADC thread
                    adc_thread.join()  # Wait for the thread to finish
                    print(f"Acquisition complete...")
                    break
                print(len(processed_sigs))
                time.sleep(10)
                print('Measuring...')
    plt.plot(filtered_ecg)
    plt.show()

    # ================================Verification=====================================   
    if mode == "Register":
        print("Template created")
        create_template(processed_sigs, dir_dict)

    print("Loading model...")
    model = model_loader.load_custom_model(dir_dict['model_path'])
    print("Model loaded")
            
    if mode == "Verification":
        result = []
        targets = np.reshape(processed_sigs, (-1, 200, 1))
        templates = np.empty((0, 200, 1))
        for template in template_data_list:
            temp_template = np.load(template, allow_pickle=True)["data"]
            temp_template = np.reshape(temp_template, (1, 200, 1))
            for i in range(targets.shape[0]):
                templates = np.concatenate((templates, temp_template), axis = 0)
            y_prob = model.predict([templates, targets])
            templates = np.empty((0, 200, 1))
            temp_result = calculate_result(y_prob, 0.8)
            result.append(temp_result)
        print(result)

    return result
        
# if __name__ == "__main__":
#     main()
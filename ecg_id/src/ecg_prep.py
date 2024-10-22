import numpy as np
import matplotlib.pyplot as plt
import neurokit2 as nk
import tensorflow as tf
import os
from tensorflow import keras
import utils
import argparse
from scipy.signal import resample, cheby1, filtfilt

class ECGPreprocessor:
    def __init__(self, frame_length=1250, step_size=100, sqa_model=None, fs=250, filter_params=None, dir_dict=None):
        self.frame_length = frame_length
        self.step_size = step_size
        self.sqa_model = sqa_model
        self.fs = fs
        self.filter_params = filter_params
        self.dir_dict = dir_dict
        self.b, self.a = self.design_chebyshev_bandpass()  # 필터 설계를 초기화 시점에 실행

    def load_data(self, data_path):
        """Data load & Get rid of corrupted labelled data frame"""
        data = np.load(data_path, allow_pickle=True)
        ecg_sigs = data['data']
        labels = data['labels'].item()
        norm_b_indices = np.where(labels['beat_type'] == 1)
        norm_r_indices = np.where(labels['rhythm_type'] == 3)
        common_elements = np.intersect1d(norm_b_indices, norm_r_indices)
        ecg_norm_sigs = ecg_sigs[common_elements]
        ecg_norm_sigs_5s = ecg_norm_sigs[:, :self.frame_length].copy()
        return ecg_norm_sigs_5s

    def apply_sqa(self, signal):
        """Apply Signal Quality Assessment (SQA)"""
        norm_sig_list = []
        corrupted_sig_list = []

        i = 0
        while (i + self.frame_length) <= len(signal):
            temp_frame = signal[i:i+self.frame_length]
            try:
                sqi = nk.ecg_quality(temp_frame, sampling_rate=self.fs, method='zhao2018')
                if sqi != "Unacceptable":
                    norm_sig_list.append(temp_frame)
                    i += self.frame_length
                else:
                    corrupted_sig_list.append(temp_frame)
                    i += self.step_size
            except:
                i += self.frame_length
                continue

        return norm_sig_list, corrupted_sig_list

    def filter_corrupted_data(self, raw_ecg_norm_5s):
        """Filter out corrupted data using SQA model"""
        y_prob = self.sqa_model.predict(raw_ecg_norm_5s)
        sqa_threshold = 0.5
        y_pred = y_prob < sqa_threshold
        clean_ecg_sigs_indx = [i for i, pred in enumerate(y_pred) if pred]
        return clean_ecg_sigs_indx

    def design_chebyshev_bandpass(self):
        """Design a Chebyshev Bandpass Filter based on filter parameters"""
        lowcut = self.filter_params['lowcut']
        highcut = self.filter_params['highcut']
        ripple = self.filter_params['ripple']
        order = self.filter_params['order']
        nyquist = 0.5 * self.fs
        low = lowcut / nyquist
        high = highcut / nyquist
        b, a = cheby1(order, ripple, [low, high], btype='band')
        return b, a

    def apply_bandpass_filter(self, signal):
        """Apply the designed bandpass filter"""
        return filtfilt(self.b, self.a, signal)

    def min_max_normalize(self, signal, feature_range=(-1, 1)):
        """Normalize signal using min-max normalization"""
        min_val = np.min(signal)
        max_val = np.max(signal)
        range_min, range_max = feature_range
        if min_val == max_val:
            return np.full_like(signal, (range_max + range_min) / 2)
        normalized_signal = (signal - min_val) / (max_val - min_val)
        normalized_signal = normalized_signal * (range_max - range_min) + range_min
        return normalized_signal

    def frame_cutter(self, norm_sig_list, pulses_per_frame=1):
        """Cut the signal into frames based on R-peaks"""
        ecg_frames = []
        for norm_sig in norm_sig_list:
            raw_ecg_norm_5s = np.reshape(norm_sig, (-1,))
            try:
                r_peaks_indx = nk.ecg_peaks(raw_ecg_norm_5s, sampling_rate=self.fs)[1]["ECG_R_Peaks"]
                for i in range(0, len(r_peaks_indx) - pulses_per_frame, pulses_per_frame):
                    r_peaks = r_peaks_indx[i:i + 1 + pulses_per_frame]
                    if all(60 <= (r_peaks[j + 1] - r_peaks[j]) <= 300 for j in range(pulses_per_frame)):
                        temp_ecg_frame = raw_ecg_norm_5s[r_peaks_indx[i]:r_peaks_indx[i + pulses_per_frame] + 1]
                        ecg_resampled_frame = resample(temp_ecg_frame, 200 * pulses_per_frame)
                        normalized_ecg_frame = self.min_max_normalize(ecg_resampled_frame)
                        ecg_frames.append(normalized_ecg_frame)
            except Exception as e:
                continue
        return ecg_frames

    
    def process(self, raw_ecg_sig, dir_dict, filter_params):
        ecg_frames = []
        if len(raw_ecg_sig) == 0:
            print('there is no signal in raw_ecg_sig')
            return np.array([])
        filtered_sig = self.apply_bandpass_filter(raw_ecg_sig)
        normalized_sig = self.min_max_normalize(filtered_sig)
        norm_sig_list, corrupted_sig_list = self.apply_sqa(normalized_sig)
        if len(norm_sig_list) == 0:
            return np.array([])
        temp_ecg_frames = self.frame_cutter(norm_sig_list)
        ecg_frames.extend(temp_ecg_frames)
        
        final_ecg_sigs_array = np.array(ecg_frames)
        return final_ecg_sigs_array
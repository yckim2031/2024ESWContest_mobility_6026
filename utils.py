import os
import argparse
import numpy as np
import tensorflow as tf
import pandas as pd
import matplotlib.pyplot as plt
import datetime

def time_info(**kwargs):
    current_time = datetime.datetime.now()
    print("Time stamp: ", current_time.strftime("%Y/%m/%d/%H:%M:%S"))
    if "past_time" in kwargs: 
        past_time = kwargs['past_time']
        elapsed_time = current_time - past_time
        print(f"Taken Time: {elapsed_time.seconds//60} min")
    return
    

# Definitive version of path finder
def path_finder(directory, file_extension, folder_conditions=None, output = True):
    """
    dir: Higher folder directory. This function finds every file under this folder.
    file_extension: file extension.
    folder_conditions: specific condition on directory. should be handled with
    list of tuple: [(folder_number, folder_name)]

    output : print count of folders this function found.
    """
    matched_files = []
    for root, dirs, files in os.walk(directory):
        path_parts = os.path.normpath(root).split(os.sep)
        if folder_conditions:
            match = True
            for n, folder_name in folder_conditions:
                if not (len(path_parts) > n and path_parts[n] == folder_name):
                    match = False
                    break
            if not match:
                continue
        for file in files:
            if file.endswith(file_extension):
                matched_files.append(os.path.join(root, file))

    if output:
        print(f"{len(matched_files)} paths are found")

    return matched_files
    
    
def gpu_config(gpu_num, gpu_mem): # GPU device & memory config
    # =================GPU_Selection==================
    gpus = tf.config.list_physical_devices('GPU')
    avail_gpu_list = [gpu.name[-1] for gpu in gpus]
    try:
        os.environ["CUDA_VISIBLE_DEVICES"] = gpu_num
        print(f"GPU {gpu_num} is selected")
    except:
        print(f"selected {gpu_num} not available.\n only {avail_gpu_list} available")

    # ================GPU_memory_occupancy============
    if gpu_num != "-1":
        if gpu_mem <= 0 or gpu_mem >= 24:
            try:
                for i in range(len(gpus)):
                	tf.config.experimental.set_memory_growth(gpus[i], True)
                print("allowing GPU memory growth. Other GPUs will be set in identical configuration")
            except RuntimeError as e:
                print("GPU memory growth allowance error")
        else:
            try:
                tf.config.set_logical_device_configuration(
                    gpus[int(gpu_num)],
                    [tf.config.LogicalDeviceConfiguration(memory_limit=1024*gpu_mem)])
                print(f"{gpu_mem} GB of memory is set")
            except RuntimeError as e:
                print("GPU memory set error")
    return

def dataset_threshold(y_data, args):
    train_size = args.train_size
    val_size = args.validation_size
    test_size = args.test_size
    req_data_size = train_size + val_size + test_size
    current_data_size = y_data.shape[0]
    if current_data_size >= req_data_size:
        return True
    else:
        print("data size is not big enough to wield the training")
        return False


def make_save_dir(dirname):
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    return

def find_files(folder_path, kind, abs_path=True):
    return [os.path.join(path, filename) if abs_path else filename
            for path, _, files in os.walk(folder_path)
            for filename in files if filename.endswith(kind)]


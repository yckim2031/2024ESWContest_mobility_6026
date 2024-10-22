import threading
from smbus2 import SMBus
import time
import lgpio
from al_detect import Al_detect
import numpy as np
import matplotlib.pyplot as plt
#import neurokit2 as nk
from queue import Queue
# checking Bus

queue = Queue()
try:
    bus=SMBus(1)
except Exception as e:
    print(f"i2c is already in use : {e}")
    bus.close()

try:
    CHIP = lgpio.gpiochip_open(0)
except Exception as e:
    print(f"GPIO is already in use : {e}")
    lgpio.gpiochip_close(CHIP)
bus = SMBus(1)

#Setting Register Address
PPG_ADDR = 0XC4 >> 1
PPG_PART_ID = 0x36

REG_IRQ_STATUS1 = 0x00
REG_IRQ_STATUS2 = 0x01
REG_IRQ_ENABLE1 = 0x02
REG_IRQ_ENABLE2 = 0x03
REG_FIFO_WRITE_PTR = 0x04
REG_FIFO_READ_PTR = 0x05
REG_OVF_COUNTER = 0x06
REG_FIFO_DATA_COUNTER = 0x07
REG_FIFO_DATA = 0x08
REG_FIFO_CONFIG1 = 0x09
REG_FIFO_CONFIG2 = 0x0A
REG_SYSTEM_CONTROL = 0x0D
REG_PPG_SYNC_CONTROL = 0x10
REG_PPG_CONFIG1 = 0x11
REG_PPG_CONFIG2 = 0x12
REG_PPG_CONFIG3 = 0x13
REG_PROX_INT_THRESHOLD = 0x14
REG_PD_BIAS = 0x15
REG_PICKET_FENCE = 0x16
REG_LED_SEQ1 = 0x20
REG_LED_SEQ2 = 0x21
REG_LED_SEQ3 = 0x22
REG_LED1_PA = 0x23
REG_LED2_PA = 0x24
REG_LED3_PA = 0x25
REG_LED_PILOT_PA = 0x29
REG_LED_RANGE1 = 0x2A
REG_S1_HI_RES_DAC1 = 0x2C
REG_S2_HI_RES_DAC1 = 0x2D
REG_S3_HI_RES_DAC1 = 0x2E
REG_S4_HI_RES_DAC1 = 0x2D
REG_S5_HI_RES_DAC1 = 0x30
REG_S6_HI_RES_DAC1 = 0x31
REG_DIE_TEMP_CONFIG = 0x40
REG_DIE_TEMP_INT = 0x41
REG_DIE_TEMP_FRACTION = 0x42
REG_DAC_CALIB_ENABLE = 0x50
REG_SHA_CMD = 0xF0
REG_SHA_CONFIG = 0xF1
REG_MEMORY_CONTROL = 0xF2
REG_MEMORY_INDEX = 0xF3
REG_MEMORY_DATA = 0xF4
REG_REV_ID = 0xFE
REG_PART_ID = 0xFF

POS_START_STOP = 1

#create maxm86161 connection function
def write_to_reg(register, value):
    bus.write_byte_data(PPG_ADDR, register, value)


    rsp = bus.read_byte(PPG_ADDR)

    return 0


def read_from_reg(register):

    value = bus.read_byte_data(PPG_ADDR, register)
    return value


def set_all_led_current(value):
    write_to_reg(REG_LED1_PA, value)
    write_to_reg(REG_LED2_PA, value)
    write_to_reg(REG_LED3_PA, value)


def set_one_bit(value, bit_position):
    return value | (1 << bit_position)


def clear_one_bit(value, bit_position):
    return value & ~(1 << bit_position)


def stop():
    existing_reg_values = read_from_reg(REG_SYSTEM_CONTROL)
    if existing_reg_values is None:
        return -1

    existing_reg_values = set_one_bit(existing_reg_values, POS_START_STOP)

    status = write_to_reg(REG_SYSTEM_CONTROL, existing_reg_values)

    return status


def start():
    existing_reg_values = read_from_reg(REG_SYSTEM_CONTROL)
    if existing_reg_values is None:
        return -1

    existing_reg_values = clear_one_bit(existing_reg_values, POS_START_STOP)

    status = write_to_reg(REG_SYSTEM_CONTROL, existing_reg_values)
    return status


def _clear_interrupt():
    read_from_reg(REG_IRQ_STATUS1)
    read_from_reg(REG_IRQ_STATUS2)


def init():
    time.sleep(0.01)
    write_to_reg(REG_SYSTEM_CONTROL, 0x09)
    time.sleep(0.001)

    
    write_to_reg(REG_SYSTEM_CONTROL, 0x0A)
    time.sleep(0.002)
    
    read_from_reg(REG_IRQ_STATUS1)
    read_from_reg(REG_IRQ_STATUS2)
    
    write_to_reg(REG_PPG_CONFIG1, 0x3F)
    
    write_to_reg(REG_PPG_CONFIG2, 0x80)
    
    write_to_reg(REG_PPG_CONFIG3, 0x40)
    
    write_to_reg(REG_PD_BIAS, 0x40)
    
    write_to_reg(REG_LED_RANGE1, 0x01)
    
    set_all_led_current(0x4F)
    
    write_to_reg(REG_SYSTEM_CONTROL, 0x0C)
    
    write_to_reg(REG_FIFO_CONFIG1, 0x7C)
    write_to_reg(REG_FIFO_CONFIG2, 0x0A)
    

    write_to_reg(REG_IRQ_ENABLE1, 0xC0)

    write_to_reg(REG_LED_SEQ1, 0x23)
    write_to_reg(REG_LED_SEQ2, 0x00)
    write_to_reg(REG_LED_SEQ3, 0x00)

    stop()

    device_id = read_from_reg(REG_PART_ID)
    _clear_interrupt()

    if device_id == PPG_PART_ID:
        return 0
    else:
        return 1



databuffer = [0] * (4 * 3)
datacounter = [0]
irq_1_data = 0
fifo_full = 0

#Setting GPIO
pin = 4
CHIP = lgpio.gpiochip_open(0)
lgpio.gpio_claim_output(CHIP, pin)
lgpio.gpio_write(CHIP, pin, 1)
data_lock = threading.Lock()
rspb = 0
rsbs = 0
reds = []
irs = []

#read ppg red,ir data
def read_ppg_data():
    global reds, irs, stop_thread, cnt
    cnt = 0
    init_status = init()
    if init_status == 0:
        start_status = start()
        while start_status == 0 and (not stop_thread):
            status = read_from_reg(REG_IRQ_STATUS1)
            irq_1_data = status
            fifo_full = (irq_1_data & 0x80) >> 7
            if fifo_full:
                cmd = [0x07]
                bus.write_i2c_block_data(PPG_ADDR, cmd[0], [])
                datacounter = bus.read_i2c_block_data(PPG_ADDR, cmd[0], 1)
                data_cnt = datacounter[0]

                cmd = [0x08]
                bus.write_i2c_block_data(PPG_ADDR, cmd[0], [])
                databuffer = bus.read_i2c_block_data(PPG_ADDR, cmd[0], 12)

                for i in range(1):
                    red_value = (databuffer[0 + 3 * i] << 16) | (databuffer[1 + 3 * i] << 8) | databuffer[2 + 3 * i]
                    red_value = red_value & 0x7FFFF
                    reds.append(-red_value)

                    ir_value = databuffer[3 + 6 * i] << 16 | databuffer[4 + 6 * i] << 8 | databuffer[5 + 6 * i]
                    ir_value = ir_value & 0x7FFFF
                    irs.append(-ir_value)
                    cnt += 1
                    #print(f"red: {red_value}, IR: {ir_value} count : {cnt}")
                fifo_full = 0
        bus.close()


# Calculating spo2
def check_spo2():
    global stop_thread, cnt, reds, irs, spo2,state
    cnt_spo2 = 0
    state = 1
    time_spo2 = 5
    while not stop_thread:
        time.sleep(time_spo2)  

        with data_lock:
            if len(reds) < 1270 or len(irs) < 1270:
                if stop_thread:
                    break
                print("there's not enough data")
                continue


            size = -256 * time_spo2
            al_detect = Al_detect(np.array(reds[size:]), np.array(irs[size:]))
            spo2 = al_detect.calculate_spo2()
            print(f"SpO2 : {spo2}")
            cnt_spo2 += 1
            

            if spo2 >= 93 and spo2 <=100:
                print("SpO2 is normal")
                peaks_3, _ = al_detect.plot_fft()
                rspb, rsbs = al_detect.calculate_RS(peaks_3, spo2 / 100)
                print(f"RSpb : {rspb}, RSbs: {rsbs}")


                stop_thread = True
                if (rspb < 5 and rsbs <1.5 and rspb > 0 and rsbs >0):
                    print("DUI detection")
                    state = 0
                    queue.put((state))
                else:
                    print("Start-up")
                    state = 1
                    queue.put((state))
                break
            elif cnt_spo2 >= 4:
                stop_thread = True
                print("measurement failure")
                state = 0
                queue.put((state))
                break
            print("SpO2 is abnormal")
            reds = []
            irs = []
            cnt = 0
    lgpio.gpiochip_close(CHIP)


def start_threads():
    global stop_thread
    stop_thread = False

    # PPG threading start
    ppg_thread = threading.Thread(target=read_ppg_data)
    ppg_thread.daemon = True
    ppg_thread.start()

    # SpO2 threading start
    spo2_thread = threading.Thread(target=check_spo2)
    spo2_thread.daemon = True
    spo2_thread.start()

    ppg_thread.join()
    spo2_thread.join()
    

#start_threads()


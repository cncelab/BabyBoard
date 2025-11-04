
# temperature.py — Modular MCC 134 Thermocouple Reader

import logging
import threading
import time
from datetime import datetime
from daqhats import mcc134, HatIDs, HatError, TcTypes
from daqhats_utils import select_hat_device, tc_type_to_string
import csv
import os

class TemperatureSensor:
    def __init__(self, tc_type=TcTypes.TYPE_K, channels=(0, 1, 2, 3), debug=False):
        self.tc_type = tc_type
        self.channels = channels
        self.hat = None
        self.running = False
        self.thread = None
        self.csv_path = None
        self.start_time = None
        self.DEBUG = debug

    def initialize(self):
        try:
            address = select_hat_device(HatIDs.MCC_134)
            self.hat = mcc134(address)
            for ch in self.channels:
                self.hat.tc_type_write(ch, self.tc_type)
            logging.info(f"MCC 134 initialized with type {tc_type_to_string(self.tc_type)}")
            return True
        except HatError as e:
            logging.error("Failed to initialize MCC 134: %s", e)
            return False

    def start(self, save_to_csv=False, csv_dir="./logs", csv_name="temperature_data.csv"):
        if not self.hat:
            if not self.initialize():
                return
        self.running = True
        if save_to_csv:
            os.makedirs(csv_dir, exist_ok=True)
            self.csv_path = os.path.join(csv_dir, csv_name)
            with open(self.csv_path, "w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["Timestamp"] + [f"Channel_{ch}" for ch in self.channels])
        self.start_time = datetime.now()
        self.thread = threading.Thread(target=self.run_loop, args=(save_to_csv,))
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def run_loop(self, save_to_csv):
        while self.running:
            readings = self.read_all()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            display = f"[{timestamp}]"
            row = [timestamp]
            for ch, temp in readings.items():
                display += f" Ch{ch}: {temp} C"
                row.append(temp)
            print(display)
            if save_to_csv and self.csv_path:
                with open(self.csv_path, "a", newline="") as file:
                    writer = csv.writer(file)
                    writer.writerow(row)
            time.sleep(1)

    def read_all(self):
        temps = {}
        for ch in self.channels:
            val = self.hat.t_in_read(ch)
            if val == mcc134.OPEN_TC_VALUE:
                temps[ch] = "Open"
            elif val == mcc134.OVERRANGE_TC_VALUE:
                temps[ch] = "OverRange"
            elif val == mcc134.COMMON_MODE_TC_VALUE:
                temps[ch] = "CommonMode"
            else:
                temps[ch] = round(val, 2)
        return temps

    def get_latest_reading(self):
        return self.read_all()


# For standalone testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    temp_sensor = TemperatureSensor(debug=True)
    try:
        temp_sensor.start(save_to_csv=True)
        print("Reading temperature... Press Ctrl+C to stop.")
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping...")
        temp_sensor.stop()


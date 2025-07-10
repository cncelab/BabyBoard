import serial
import csv
import os
from datetime import datetime
import xml.etree.ElementTree as ET
import threading
import time

class IRGA:
    def __init__(self, port='/dev/ttyUSB0', baud_rate=9600, debug=False):
        self.serial_port = serial.Serial(port, baud_rate, timeout=1)
        self.DEBUG = debug
        self.running = False
        self.csv_path = None
        self.start_time = None
        self.thread = None

    def read_sensor_data(self):
        try:
            xml_data = self.serial_port.readline().decode('utf-8').strip()
            if self.DEBUG:
                print(f"IRGA XML: {xml_data}")
            return xml_data
        except:
            return None

    def parse_xml_data(self, xml_data):
        try:
            root = ET.fromstring(xml_data)
            co2 = float(root.find('./data/co2').text)
            h2o = float(root.find('./data/h2o').text)
            temp = float(root.find('./data/celltemp').text)
            return co2, h2o, temp
        except:
            return None, None, None

    def parse_xml_data(self, xml_data):
        try:
            root = ET.fromstring(xml_data)
            co2 = float(root.find('./data/co2').text)
            h2o = float(root.find('./data/h2o').text)
            temp = float(root.find('./data/celltemp').text)
            cellpressure = float(root.find('./data/cellpressure').text)
            h2odewpoint = float(root.find('./data/h2odewpoint').text)
            return co2, h2o, temp, cellpressure, h2odewpoint
        except:
            return None, None, None, None, None


    def start(self, save_to_csv=False, csv_dir="/home/asucnce/baby/logs", csv_name="irga_data.csv"):
        self.running = True
        if save_to_csv:
            os.makedirs(csv_dir, exist_ok=True)
            self.csv_path = os.path.join(csv_dir, csv_name)
            with open(self.csv_path, "w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["Timestamp", "CO2", "H2O", "Temperature", "CellPressure", "H2ODewPoint"])
        self.start_time = datetime.now()
        self.thread = threading.Thread(target=self.run_loop, args=(save_to_csv,))
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        self.serial_port.close()

    def run_loop(self, save_to_csv):
        while self.running:
            xml_data = self.read_sensor_data()
            if xml_data:
                co2, h2o, temp, cellpressure, h2odewpoint = self.parse_xml_data(xml_data)
                if co2 is not None:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    print(f"[{timestamp}] CO2: {co2} ppm, H2O: {h2o} g/m³, Temp: {temp} °C, Pressure: {cellpressure} mbar, DewPt: {h2odewpoint} °C")

                    if save_to_csv and self.csv_path:
                        with open(self.csv_path, "a", newline="") as file:
                            writer = csv.writer(file)
                            writer.writerow([timestamp, co2, h2o, temp, cellpressure, h2odewpoint])
            time.sleep(1)

    def get_latest_reading(self):
        xml_data = self.read_sensor_data()
        if xml_data:
            return self.parse_xml_data(xml_data)
        return None, None, None


# ✅ For standalone testing
if __name__ == "__main__":
    irga_sensor = IRGA(debug=True)
    try:
        irga_sensor.start(save_to_csv=True)
        print("Reading... Press Ctrl+C to stop.")
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopping...")
        irga_sensor.stop()

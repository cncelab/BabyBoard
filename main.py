import argparse
import time
import os
import csv
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from gpiozero import OutputDevice
from IRGA import IRGA
from temprature import TemperatureSensor
from rich.live import Live
from rich.table import Table

# Globals
irga_sensor = None
temp_sensor = None

def ask_yes_no(prompt: str, default: bool = True) -> bool:
    default_txt = "Y/n" if default else "y/N"
    while True:
        resp = input(f"{prompt} [{default_txt}]: ").strip().lower()
        if not resp:
            return default
        if resp in ("y", "yes"):
            return True
        if resp in ("n", "no"):
            return False
        print("Please answer 'y' or 'n'.")

def run_cli():
    global irga_sensor, temp_sensor

    # === Step 1: Mode ===
    state = input("Enter starting experiment state (wet/dry): ").strip().lower()
    if state not in ("wet", "dry"):
        print("❌ Invalid choice. Please run again with 'wet' or 'dry'.")
        return
    print(f"✅ Experiment will START in {state.upper()} mode.")

    # === Step 1B: Save CSV? ===
    save_csv = ask_yes_no("Do you want to save sensor data to CSV?", default=True)
    print(f"✅ CSV logging: {'ON' if save_csv else 'OFF'}")

    # === Step 2: Directory ===
    csv_dir = "/home/asucnce/baby/logs"
    csv_path = None
    if save_csv:
        user_dir = input(f"Enter directory to save CSVs (press Enter for default: {csv_dir}): ").strip()
        if user_dir:
            csv_dir = user_dir
        os.makedirs(csv_dir, exist_ok=True)
        print(f"✅ CSV directory set to: {csv_dir}")

        # === Step 3: Filename ===
        filename = input("Enter CSV filename (without extension, default = experiment_log): ").strip()
        if not filename:
            filename = "experiment_log"
        filename = filename.replace("/", "_").replace("\\", "_")  # sanitize
        csv_path = os.path.join(csv_dir, f"{filename}.csv")
        print(f"✅ CSV file will be saved as: {csv_path}")

    # === Step 4: H₂O setpoint ===
    while True:
        try:
            h2o_setpoint = float(input("Enter H₂O setpoint (in mmol/mol): ").strip())
            if h2o_setpoint < 0:
                raise ValueError("Setpoint must be a non-negative number.")
            break
        except ValueError as e:
            print(f"❌ Invalid input. {e}")

    print(f"✅ H₂O Setpoint entered: {h2o_setpoint:.2f} mmol/mol")

    # === Step 5: Cycle time ===
    try:
        cycle_time_min = float(input("Enter cycle time in minutes (default = 80): ").strip() or "80")
    except ValueError:
        cycle_time_min = 80.0
    cycle_time = timedelta(minutes=cycle_time_min)


    print(f"✅ Cycle time set to {cycle_time_min} minutes.")

    # === Setup sensors ===
    shared_pin = OutputDevice(14)
    irga_sensor = IRGA(debug=False)
    temp_sensor = TemperatureSensor(channels=(0,), debug=True)

    irga_sensor.start(save_to_csv=save_csv)
    temp_sensor.start(save_to_csv=save_csv)

    # === Prepare CSV ===
    csv_file, csv_writer = None, None
    if save_csv and csv_path:
        csv_file = open(csv_path, mode="w", newline="")
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow([
            "timestamp", "cycle_state", "elapsed_min",
            "co2_ppm", "h2o_mmol", "irga_temp_C",
            "pressure_kPa", "dewpoint_C", "temp_ch0_C", "gpio_state"
        ])

    # === Real-time plot setup ===
    plt.ion()
    fig, axs = plt.subplots(4, 1, figsize=(10, 8), sharex=True)

    times, co2_vals, h2o_vals, temp_vals, gpio_vals = [], [], [], [], []

    axs[0].set_ylabel("Temp (°C)")
    axs[1].set_ylabel("CO₂ (ppm)")
    axs[2].set_ylabel("H₂O (mmol/mol)")
    axs[3].set_ylabel("Valve")
    axs[3].set_xlabel("Time")

    for ax in axs:
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))

    print("⌛ Waiting for sensors to warm up...")
    while irga_sensor.get_latest_reading() is None or temp_sensor.get_latest_reading() is None:
        time.sleep(0.5)

    experiment_start = datetime.now()
    last_switch = experiment_start

    print(f"🔥 Running {state.upper()} mode control loop... Press Ctrl+C to stop\n")

    try:
        with Live(refresh_per_second=1, screen=False) as live:
            while True:
                now = datetime.now()
                elapsed = now - experiment_start

                # Auto-switch mode if cycle time reached
                if now - last_switch >= cycle_time:
                    state = "dry" if state == "wet" else "wet"
                    last_switch = now
                    print(f"🔄 Auto-switched mode to {state.upper()} after {cycle_time_min} mins")

                irga = irga_sensor.get_latest_reading()
                temp_data = temp_sensor.get_latest_reading()

                table = Table(title=f"Sensor Dashboard — {state.upper()} Mode")
                table.add_column("Sensor", style="cyan", no_wrap=True)
                table.add_column("Value", style="magenta")

                table.add_row("CSV Logging", "ON" if save_csv else "OFF")
                if save_csv and csv_path:
                    table.add_row("CSV Path", csv_path)

                # Show elapsed time and cycle time
                table.add_row("Elapsed Time", str(elapsed).split(".")[0])
                table.add_row("Cycle Time", f"{cycle_time_min:.0f} min")

                row = {
                    "timestamp": now.isoformat(),
                    "cycle_state": state,
                    "elapsed_min": round(elapsed.total_seconds() / 60, 2),
                    "co2": None, "h2o": None,
                    "irga_temp": None, "pressure": None,
                    "dewpoint": None, "temp_ch0": None,
                    "gpio_state": None
                }

                # IRGA readings
                if irga and all(v is not None for v in irga):
                    co2, h2o, temp_irga, pressure, dewpoint = irga
                    table.add_row("CO2 (ppm)", f"{co2:.2f}")
                    table.add_row("H2O (mmol/mol)", f"{h2o:.2f}")
                    table.add_row("IRGA Temp (°C)", f"{temp_irga:.2f}")
                    table.add_row("Pressure (kPa)", f"{pressure:.2f}")
                    table.add_row("Dew Point (°C)", f"{dewpoint:.2f}")
                    row.update({"co2": co2, "h2o": h2o,
                                "irga_temp": temp_irga,
                                "pressure": pressure,
                                "dewpoint": dewpoint})
                else:
                    table.add_row("IRGA", "Waiting...")

                # Temperature & control
                if temp_data:
                    temp_ch0 = temp_data.get(0)
                    if isinstance(temp_ch0, float):
                        table.add_row("Temp Ch0 (°C)", f"{temp_ch0:.2f}")
                        row["temp_ch0"] = temp_ch0

                        if state == "wet":
                            if temp_ch0 < 27.0:
                                shared_pin.off(); gpio_state = "ON"
                            else:
                                shared_pin.on(); gpio_state = "OFF"
                        elif state == "dry":
                            if temp_ch0 > -10.0:
                                shared_pin.on(); gpio_state = "ON"
                            else:
                                shared_pin.off(); gpio_state = "OFF"
                        table.add_row("GPIO4", gpio_state)
                        row["gpio_state"] = gpio_state
                else:
                    table.add_row("Temp Sensor", "Waiting...")
                    shared_pin.off()
                    table.add_row("GPIO4", "OFF")
                    row["gpio_state"] = "OFF"

                # Write CSV
                if save_csv and csv_writer:
                    csv_writer.writerow([
                        row["timestamp"], row["cycle_state"], row["elapsed_min"],
                        row["co2"], row["h2o"], row["irga_temp"],
                        row["pressure"], row["dewpoint"], row["temp_ch0"], row["gpio_state"]
                    ])
                    csv_file.flush()

                # === Update plots ===
                times.append(now)
                co2_vals.append(row["co2"])
                h2o_vals.append(row["h2o"])
                temp_vals.append(row["temp_ch0"])
                gpio_vals.append(1 if row["gpio_state"] == "ON" else 0)

                axs[0].cla(); axs[0].plot(times, temp_vals, color="orange"); axs[0].set_ylabel("Temp (°C)")
                axs[1].cla(); axs[1].plot(times, co2_vals, color="green"); axs[1].set_ylabel("CO₂ (ppm)")
                axs[2].cla(); axs[2].plot(times, h2o_vals, color="blue"); axs[2].set_ylabel("H₂O (mmol/mol)")
                axs[3].cla(); axs[3].step(times, gpio_vals, where="post", color="red"); axs[3].set_ylabel("Valve")
                axs[3].set_xlabel("Time")

                plt.draw()
                plt.pause(0.01)

                live.update(table)
                time.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 Experiment stopped by user.")
    finally:
        try:
            irga_sensor.stop()
            temp_sensor.stop()
        except Exception:
            pass
        shared_pin.off()
        if csv_file:
            csv_file.close()
            print(f"💾 Data saved to {csv_path}")

        plt.ioff()
        plt.show()

def run_gui():
    print("GUI mode not implemented yet.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Control system CLI/GUI")
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode")
    parser.add_argument("--gui", action="store_true", help="Run in GUI mode")
    args = parser.parse_args()

    if args.cli:
        run_cli()
    elif args.gui:
        run_gui()
    else:
        print("Please run with either --cli or --gui")
        print("Example: python3 control_realtime.py --cli")

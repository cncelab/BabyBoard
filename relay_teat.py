# test_heater.py — simple GPIO on/off loop test
from gpiozero import OutputDevice
import time

# Initialize GPIO4 as output
heater = OutputDevice(14)

print("Starting heater GPIO test. Press Ctrl+C to stop.")
try:
    while True:
        # Turn ON
        heater.on()
        print("🔥 Heater ON (GPIO4 ON)")
        time.sleep(3)

        # Turn OFF
        heater.off()
        print("🧊 Heater OFF (GPIO4 OFF)")
        time.sleep(3)

except KeyboardInterrupt:
    print("\nTest stopped by user. Turning heater OFF.")
    heater.off()

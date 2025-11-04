

project:
  # BabyBoard



  requirements:
    hardware:
      - Raspberry Pi (Model 3B or higher recommended)
      - MCC 134 DAQ HAT
      - Supported thermocouples: J, K, T, E, R, S, B, N
      - Relay device on GPIO4
    software:
      - Python 3.7+
      - pip packages:
          - daqhats
          - gpiozero
          - matplotlib
          - rich

  installation:
    steps:
      - git clone https://github.com/<your-username>/<your-project-name>.git
      - cd <your-project-name>
      - pip install -r requirements.txt
      - (Or install individually): pip install daqhats gpiozero matplotlib rich
      - Set up hardware: MCC 134 DAQ HAT, thermocouples, relay on GPIO4

  usage:
    cli_mode:
      command: python3 main.py --cli
      description: >
        Runs the control loop with dashboard, data logging, and relay/valve control. Interactive setup for mode, CSV, timing, setpoints.
    gui_mode:
      command: python3 main.py --gui
      description: >
        (Experimental, not implemented)
    temperature_logging:
      command: python3 temprature.py
      description: Logs temperature readings to CSV and prints to terminal.
    relay_test:
      command: python3 relay_teat.py
      description: Cycles GPIO4 on/off every 3 seconds to test relay function.

  project_structure:
    main.py: CLI + control loop + logging + dashboard
    temprature.py: MCC 134 DAQ HAT threaded temperature logger
    daqhats_utils.py: MCC DAQ HAT hardware abstraction helpers
    relay_teat.py: Minimal relay (GPIO) test routine


  authors:
    - Vipul Jethwa (vjethwa1@asu.edu)
    - Arizona State University, Center for Negative Carbon Emissions


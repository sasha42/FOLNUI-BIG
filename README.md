# FOLNUI BIG installation

* ✨  Code for an interactive **art installation**
* 💁‍♀️  **Detect people** with ultrasonic sensors
* 🎹  Send out a MIDI to trigger **animations in Madmapper**

## Functionality
At boot, the code will perform the following:
1. **Calibrate sensors** on boot, the code will calibrate the nominal and threshold valuse for the sensors, so that it can automatically detect the distance
2. **Pick a MIDI device** next, where it will choose the first MIDI device (typically on USB)
3. **Connect to websocket** it will then connect to an internal websocket server, so that you can monitor what's happening from your phone

After booting, it will run the following loop:
1. **Measure distance** for each sensor
2. **Check threshold** to see if the distance is within our trigger distance (e.g. the sensor detects a person underneath it)
3. **Check last values** if the distance is within the trigger distance, check whether the last measured value also detected a person
4. **Send MIDI and Websocket signal** if the last 2 values triggered for a sensor, send out a MIDI note (*e.g. Note On for Note 60*) and Websocket message
4. **Check multiple sensors** if there are multiple sensors, send another MIDI note based on number of simultaneous triggers (*e.g. Note On on Note 72 for 2 sensors triggered simultaneously**)

The above loop runs at approximately 10fps.

## Setup
The project is intended to run on a Raspberry Pi. Basic knowledge of how to use the linux command line is assumed.
```
# Download project
git clone https://github.com/sasha42/FOLNUI-BIG.git
cd FOLNUI-BIG/

# Update your Pi and install packages
sudo apt-get update
sudo apt-get upgrade
sudo apt-get install apache2 mosh vim hostapd dnsmasq

# Set up virtual env
sudo pip3 install virtualenv
virtualenv venv
source venv/bin/activate

# Install the dependencies
pip install -r requirements.txt

# Create a websocket service that starts on boot
sudo cp folnui-websocket.service /lib/systemd/system/folnui-websocket.service
systemctl start folnui-websocket
systemctl enable folnui-websocket

# Create sensor reading service to start on boot
sudo cp folnui-sensor.service /lib/systemd/system/folnui-sensor.service
systemctl start folnui-sensor
systemctl enable folnui-sensor

# Set up the wifi access point
sudo DEBIAN_FRONTEND=noninteractive apt install -y netfilter-persistent iptables-persistent
sudo systemctl unmask hostapd
sudo systemctl enable hostapd

# Configure files for wifi access point
sudo echo -e "interface wlan0\n  static ip_address=192.168.4.1/24\n  nohook wpa_supplicant" >> /etc/dhcpcd.conf

# Copy html files into apache2 directory
sudo cp ~/FOLNUI-BIG/html/* /var/www/html/.

# Reboot pi, everything should run after reboot
sudo reboot
```

## Config
After running the code on the Pi, you should be able to connect automatically to 7 sensors and a MIDI output device. You can configure the sensors ahead of time in the `responsive-midi-logging.py` file, where you'll see stuff like this:
```
    "1": {"gpioPin": 4,
          "midiChannel": 61,
          "active": True,
          "lastVals": [],
          "nominal": 70,
          "threshold": 35}
```

This enables you to change a bunch of stuff:
* **gpioPin**: BCM pin of the Raspberr Pi GPIO to which the sensor is connected to
* **midiChannel**: MIDI channel where a note will be sent to when sensor is triggered
* **active**: Boolean of whether this sensor is active or not, in case a sensor is missing
* **lastVals**: List for internal use - do not modify
* **nominal**: The default distance **Note: the code calibrates on start and sets this value itself**
* **threshold**: Trigger threshold for the sensor, beyond this distance it will trigger

The Pi will automatically connect to the first MIDI device it sees. If there's no MIDI device, nothing will happen.

---

❤️
# FOLNUI BIG installation

Code for an art installation.

This code detects the presence of a person and triggers a midi signal.

## Setup
```
# Download project
git clone https://github.com/sasha42/FOLNUI-BIG.git
cd FOLNUI-BIG/

# Set up virtual env
sudo pip3 install virtualenv
virtualenv venv
source venv/bin/activate

# Install the dependencies
pip install -r requirements.txt

# Create a system service that starts on boot
sudo cp folnui.service /lib/systemd/system/folnui.service
systemctl start folnui
systemctl enable folnui

# Reboot pi, everything should run after reboot
sudo reboot
```

## Config
There is a lot of hardcoded stuff because this codebase was written in a day.

**MIDI device**
Uncomment the code on line 77 of `responsive-midi.py` to get a list of MIDI USB devices. Copy the name of the device you want to use, and put it into line 78. It should look like this:
```
output = mido.open_output('ESI MIDIMATE eX:ESI MIDIMATE eX MIDI 1 24:0')
```

**Detection sensitivity**
The sensor is very sensitive and can provide a fairly accurate measurement. We do not use accuracy and instad have a binary thing. Super hacky code can be found between lines 57 and 69 of `responsive-midi.py`.

 he two key changes are the following, to be adjusted to the height of where the sensor is located:
```
max_distance = 268.4
min_distance = 50.5
``` 

**Distance measurement**
Run `python distance.py` to get the distance from the sensor.

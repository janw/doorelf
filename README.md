# 🧝‍♂️ Doorelf — wireless doorbell Slack notifications

Doorelf is a small python daemon to be run on a Raspberry Pi equipped with an RF receiver (433/315 MHz). It listens for the signals from the doorbell button, and sends a Slack notification to a configured channel when somebody rings at the door.

Doorelf has been tested with the following wireless / RF doorbell products:

- [TeckNet WA 1078 / 1088](https://www.amazon.de/dp/B01BI57H06/)

Technically it should work™ with almost any 433 or 315MHz product, as the [underlying RF library, rpi_rf](https://github.com/milaq/rpi-rf) handles all signal logic in a generalized way, and only passes the received codes on to Doorelf.

## Requirements and setup

Doorelf requires an RF receiver to be connected to your Pi. Instructions on how to deal with the hardware side of things can be found in [this Instructables How-To](https://www.instructables.com/id/Super-Simple-Raspberry-Pi-433MHz-Home-Automation/).

For the software to run, first install the necessary packages via apt as Raspbian Lite does have neither git nor pip installed. Doorelf so far has only been tested with python3 provided by Raspbian Lite (currently v3.5).

```
sudo apt update
sudo apt install git python3-pip -y
```

Now clone the repo, install the Python dependencies, and make sure to adjust the configuation file to match your setup — most notably, set the Slack Webhook URL, that you get after adding an [Incoming Webhook to your space](https://slack.com/apps/A0F7XDUAZ-incoming-webhooks).

```
git clone https://github.com/janw/doorelf.git ~/doorelf
cd ~/doorelf

# Install requirements via pip
pip3 install -r requirements.txt

# Modify config.ini
vi config.ini
```

Before starting the daemon for the first time, symlink the systemd service into place, reload, and enable the service.

```
sudo ln -s /home/pi/doorelf/doorelf.service /etc/systemd/system/
sudo systemctl --system daemon-reload
sudo systemctl enable doorelf.service
```


## Starting and running the daemon

Now you're ready to start the daemon. Wait a few seconds to check its status.

```
sudo systemctl start doorelf.service
sudo systemctl status doorelf.service
```

The status should look as follows:

```
● doorelf.service - Doorelf, the doorbell Slack integration
   Loaded: loaded (/home/pi/doorelf/doorelf.service; enabled; vendor preset: enabled)
   Active: active (running) since Wed 2019-02-06 18:12:25 GMT; 1s ago
     Docs: https://github.com/janw/doorelf
 Main PID: 4439 (python3)
   CGroup: /system.slice/doorelf.service
           └─4439 /usr/bin/python3 /home/pi/doorelf/daemon.py
```


## Setup for your actual doorbell

By default DEBUG output is enabled in `config.ini`. This way you'll be able to determine the doorbell code from the systemd status output. Simply press the doorbell button from within a reasonable distance of the Pi/receiver, and shortly after check `sudo systemctl status doorelf.service` again. You should see a few lines like this one:

```
… doorelf 2019-02-06 18:13:15,175 [DEBUG] Received code 111110001100010100001000 (pulselen 109; proto 109).
```

If that appears multiple times it's fairly safe to assume it's your doorbell. 😄

Enter the code in the `config.ini` and run `sudo systemctl restart doorelf.service
`.

import time
from os import path
import logging
import requests
from configparser import ConfigParser
from rpi_rf import RFDevice
import sdnotify
HERE = path.dirname(path.realpath(__file__))

config = ConfigParser()
config.read(path.join(HERE, 'config.ini'))

RECEIVE_PIN = config['hardware'].getint('gpio_pin', 18)
DOORBELL_CODE = config['hardware'].get('doorbell_code', '11101111')

SLACK_WEBHOOK_URL = config['notifier']['slack_webhook_url']
PAYLOAD_FILE = config['notifier'].get('payload_file', './payload.json')
SLEEP_NOTIFIER_SEC = config['notifier'].getint('sleep_notifier_sec', 4)

logger = logging.getLogger(__name__)

with open(PAYLOAD_FILE) as payload_file:
    payload = payload_file.read()

systemd = sdnotify.SystemdNotifier()


def send_notification(self):
    response = requests.post(SLACK_WEBHOOK_URL, data={'payload': payload})
    logger.debug("Got response {} from Slack API".format(response.status_code))
    if response.status_code != 200:
        logger.debug(response.json())


def listener():
    rfdevice = RFDevice(RECEIVE_PIN)
    rfdevice.enable_rx()
    timestamp = None
    logger.info("Listening on GPIO {}".format(RECEIVE_PIN))
    systemd.notify("READY=1")
    while True:
        if rfdevice.rx_code_timestamp != timestamp:
            timestamp = rfdevice.rx_code_timestamp
            binary_code = "{:b}".format(rfdevice.rx_code)
            logger.debug("Received code {} (pulselen {}; proto {}).".format(
                binary_code, rfdevice.rx_pulselength, rfdevice.rx_pulselength))

            if binary_code == DOORBELL_CODE:
                logger.info("Received valid code. Notifying now.")
                send_notification()
                logger.debug("Going to sleep for {} seconds".format(SLEEP_NOTIFIER_SEC))
                time.sleep(SLEEP_NOTIFIER_SEC)
        time.sleep(0.01)


def main():
    try:
        listener()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt. Quitting.")
        systemd.notify("STOPPING=1")
    except Exception as ctx:
        logger.exception("Unhandled exception during execution.", ecx_info=True)
        systemd.notify("STATUS=An exception occured: {}\n ERRNO=1".format(ctx.message))


if __name__ == '__main__':
    main()

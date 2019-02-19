import time
import sys
from os import path
import logging
import requests
from configparser import ConfigParser
from rpi_rf import RFDevice
import sdnotify

LOGGING_FORMAT = '%(name)s %(asctime)-15s [%(levelname)s] %(message)s'
logging.basicConfig(format=LOGGING_FORMAT)

HERE = path.dirname(path.realpath(__file__))
config = ConfigParser()
config.read(path.join(HERE, 'config.ini'))
logger = logging.getLogger(name='doorelf')
logger.setLevel(config['default'].get('loglevel', 'INFO').upper())

RECEIVE_PIN = config['hardware'].getint('gpio_pin', 18)
DOORBELL_CODE = config['hardware'].get('doorbell_code', '11101111')

SLACK_WEBHOOK_URL = config['notifier']['slack_webhook_url']
PAYLOAD_FILE = config['notifier'].get('payload_file', './payload.json')
SLEEP_NOTIFIER_SEC = config['notifier'].getint('sleep_notifier_sec', 4)
RETRY_DELAY_SEC = config['notifier'].getint('retry_delay_sec', 3)


with open(PAYLOAD_FILE) as payload_file:
    payload = payload_file.read()

systemd = sdnotify.SystemdNotifier()


class RetriesExhaustedError(ConnectionError):
    pass


def send_notification():
    retries = 2
    trial = 0

    while trial <= retries:
        try:
            response = requests.post(SLACK_WEBHOOK_URL, data={'payload': payload})
            logger.debug("Got response {} from Slack API".format(response.status_code))
            if response.status_code == 200:
                return
            logger.error("Failed to notify Slack: code {}".format(response.status_code))

        except ConnectionError:
            logger.error(
                "ConnectionError notifying Slack. Trying again in {} sec".format(
                    RETRY_DELAY_SEC
                ),
                exc_info=True
            )
            systemd.notify("WATCHDOG=1")
            time.sleep(RETRY_DELAY_SEC)
        trial += 1

    raise RetriesExhaustedError("Exhausted maximum number of retries")


def listener(rfdevice):
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
                logger.debug("Going to sleep for {} seconds.".format(SLEEP_NOTIFIER_SEC))
                time.sleep(SLEEP_NOTIFIER_SEC)
                logger.debug("Continuing listening.")
            timestamp = rfdevice.rx_code_timestamp
        systemd.notify("WATCHDOG=1")
        time.sleep(0.05)


def main():

    try:
        rfdevice = RFDevice(RECEIVE_PIN)
        listener(rfdevice)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt. Quitting.")
        systemd.notify("STOPPING=1")
        rfdevice.cleanup()
        sys.exit(0)
    except Exception as ctx:
        logger.exception("Unhandled exception during execution.", exc_info=True)
        systemd.notify("STATUS=An exception occured.\nERRNO=1")
        rfdevice.cleanup()
        sys.exit(1)


if __name__ == '__main__':
    main()

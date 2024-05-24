"""
main.py
04. December 2023

automatically restarts ssh-tunnels

Author:
Nilusink
"""
from time import sleep, strftime
from subprocess import Popen
from urllib import request
from datetime import time
import logging
import signal
import sys


SERVICE_NAME: str = "ssh_tunnels"
PRIVATE_HOST: str = "http://server.nilus.ink:20080"
PUBLIC_HOST: str = "http://server.nilus.ink:80"
PING_INTERVAL: time = time(minute=2)


def time_to_seconds(t: time) -> int:
    """
    converts time dataclass to only seconds (add up hours + minutes + seconds)

    :param t: input time
    :return: equivalent time in seconds
    """
    return t.second + t.minute * 60 + t.hour * 3600


def check_connection(server: str, timeout: float = 5) -> bool:
    """
    tries to request a GET from the given server

    :return: server reachable or nit
    """
    request.urlopen(url=server, timeout=timeout)
    try:
        request.urlopen(url=server, timeout=timeout)
        return True

    except request.URLError:
        return False


class PingPong:
    running: bool

    def __init__(self) -> None:
        self.running = True

    @staticmethod
    def ping() -> None:
        """
        sends out a ping (to itself, technically)
        """
        # try to connect to server
        if check_connection(PRIVATE_HOST):
            logging.info(f"{strftime('%c')}: ping OK")

        else:
            # in case of TimeoutError, restart the ssh_tunnel service
            logging.warning(f"{strftime('%c')}: ping FAIL")

            # try if internet is reachable
            if check_connection(PUBLIC_HOST):
                logging.warning(
                    f"{strftime('%c')}: internet reachable, RESTARTING"
                )
                Popen(["sudo", "systemctl", "restart", SERVICE_NAME])

            else:
                logging.error(f"{strftime('%c')}: internet UNREACHABLE")

    def run(self) -> None:
        """
        starts both client and server
        """
        logging.info(f"{strftime('%c')}: starting server")

        while self.running:
            self.ping()

            # wait for next iteration
            sleep(time_to_seconds(PING_INTERVAL))

    def close(self) -> None:
        """
        stop all running processes
        """
        logging.info(f"{strftime('%c')}: shutting down")
        self.running = False

        exit(0)


if __name__ == "__main__":
    logging.basicConfig(
        filename="reconnector.log",
        encoding="utf-8",
        level=logging.WARNING,
    )

    # add handler to also print to stdout
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

    pp = PingPong()
    signal.signal(signal.SIGINT, lambda *_: pp.close())
    signal.signal(signal.SIGTERM, lambda *_: pp.close())

    pp.run()
    pp.close()

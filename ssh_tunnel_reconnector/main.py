"""
main.py
04. December 2023

automatically restarts ssh-tunnels

Author:
Nilusink
"""
from time import sleep, strftime
from threading import Thread
from subprocess import Popen
from urllib import request
from datetime import time
import logging
import socket
import signal
import sys


SERVICE_NAME: str = "ssh_tunnels"
PUBLIC_HOST: str = "server.nilus.ink"
PUBLIC_I_HOST: str = "http://server.nilus.ink:80"
PING_INTERVAL: time = time(minute=2)
ON_FAIL_DELAY: time = time(second=10)
PORT: int = 20000


def time_to_seconds(t: time) -> int:
    """
    converts time dataclass to only seconds (add up hours + minutes + seconds)

    :param t: input time
    :return: equivalent time in seconds
    """
    return t.second + t.minute * 60 + t.hour * 3600


def check_connection(server: str = PUBLIC_I_HOST, timeout: float = 5) -> bool:
    """
    tries to request a GET from the given server

    :return: server reachable or nit
    """
    try:
        request.urlopen(url=server, timeout=timeout)
        return True

    except request.URLError:
        return False


class PingPong:
    running: bool

    def __init__(self) -> None:
        # create server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(("0.0.0.0", PORT))
        self._server_socket.setblocking(False)
        self._server_socket.settimeout(time_to_seconds(ON_FAIL_DELAY))
        self._server_socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1
        )
        self._server_socket.listen()

        self.running = True

    def accept_ping(self) -> None:
        """
        waits for clients (itself) to connect and sends an 8-byte long message
        """
        while self.running:
            # start client
            t = Thread(target=self.ping)
            t.start()

            # using timeouts because otherwise the sock_accept function wouldn't
            # notice self.running being set to false
            try:
                client, _ = self._server_socket.accept()

            except TimeoutError:
                sleep(time_to_seconds(ON_FAIL_DELAY))
                continue

            client.sendall(b"-hellow-")
            client.close()

            # wait for client thread to finish
            t.join()

            # wait for next iteration
            # No need to constantly check for self.running, since `exit` is
            # called anyway and this function runs in the same thread.
            sleep(time_to_seconds(PING_INTERVAL))

    @staticmethod
    def ping() -> None:
        """
        sends out a ping (to itself, technically)
        """
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(10)

        try:
            # try to connect to server
            client.connect((PUBLIC_HOST, PORT))
            client.recv(8)
            logging.info(f"{strftime('%c')}: ping OK")

        except (TimeoutError, ConnectionRefusedError):
            # in case of TimeoutError, restart the ssh_tunnel service
            logging.warning(f"{strftime('%c')}: ping FAIL")

            # try if internet is reachable
            if check_connection():
                logging.warning(
                    f"{strftime('%c')}: internet reachable, RESTARTING"
                )
                Popen(["sudo", "systemctl", "restart", SERVICE_NAME])

            else:
                logging.error(f"{strftime('%c')}: internet UNREACHABLE")

        finally:
            client.close()

    def run(self) -> None:
        """
        starts both client and server
        """
        self.accept_ping()

    def close(self) -> None:
        """
        stop all running processes
        """
        logging.info(f"{strftime('%c')}: shutting down")

        self._server_socket.shutdown(socket.SHUT_RDWR)
        self._server_socket.close()
        self.running = False

        exit(0)


if __name__ == "__main__":
    # configure logging
    logging.basicConfig(
        filename="reconnector.log",
        encoding="utf-8",
        level=logging.INFO,
    )

    # add handler to also print to stdout
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))

    # create PingPong instance
    pp = PingPong()

    # intercept SIGINT and SIGTERM
    signal.signal(signal.SIGINT, lambda *_: pp.close())
    signal.signal(signal.SIGTERM, lambda *_: pp.close())

    # start the reconnector
    pp.run()
    pp.close()

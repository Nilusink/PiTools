from asyncio import gather, sleep, new_event_loop, set_event_loop
from asyncio import get_event_loop
from subprocess import Popen
from datetime import time
import socket
import signal


SERVICE_NAME: str = "ssh_tunnels"
PUBLIC_HOST: str = "server.nilus.ink"
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


class PingPong:
    running: bool

    def __init__(self) -> None:
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(("0.0.0.0", PORT))
        self._server_socket.setblocking(False)
        self._server_socket.settimeout(10)
        self._server_socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1
        )
        self._server_socket.listen()

        self.running = True

    async def accept_ping(self) -> None:
        """
        waits for clients (itself) to connect and sends an 8-byte long message
        """
        async_loop = get_event_loop()
        while self.running:
            # using timeouts because otherwise the sock_accept function wouldn't
            # notice self.running being set to false
            try:
                client, _ = await async_loop.sock_accept(self._server_socket)

            except TimeoutError:
                continue

            await async_loop.sock_sendall(client, b"-hellow-")
            client.close()

    async def periodic_ping(self) -> None:
        """
        periodically sends out pings (to itself, technically)
        """
        # give the server some time before the clients first ping
        await sleep(time_to_seconds(ON_FAIL_DELAY))

        async_loop = get_event_loop()
        while self.running:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(10)

            try:
                client.connect((PUBLIC_HOST, PORT))
                await async_loop.sock_recv(client, 8)
                print("ping worked")

            except TimeoutError:
                print("couldn't reach, restarting")
                Popen(["sudo", "systemctl", "restart", SERVICE_NAME])
                await sleep(time_to_seconds(ON_FAIL_DELAY))
                continue

            finally:
                await sleep(time_to_seconds(PING_INTERVAL))
                client.close()

    async def run(self) -> None:
        """
        starts both client and server
        """
        await gather(
            self.accept_ping(),
            self.periodic_ping()
        )

    def close(self) -> None:
        """
        stop all running processes
        """
        self.running = False


if __name__ == "__main__":
    pp = PingPong()
    signal.signal(signal.SIGINT, lambda *_: pp.close())
    signal.signal(signal.SIGTERM, lambda *_: pp.close())

    loop = new_event_loop()
    set_event_loop(loop)
    loop.run_until_complete(pp.run())
    pp.close()

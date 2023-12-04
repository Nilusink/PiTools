from asyncio import gather, sleep, new_event_loop, set_event_loop
from asyncio import get_event_loop
from subprocess import Popen
from datetime import time
import socket
import signal


SERVICE_NAME: str = "ssh_tunnels"
PUBLIC_HOST: str = "128.0.0.1"
PING_INTERVAL: time = time(second=2)
PORT: int = 20000


class PingPong:
    running: bool

    def __init__(self) -> None:
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(("0.0.0.0", PORT))
        self._server_socket.setblocking(False)
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
            client, _ = await async_loop.sock_accept(self._server_socket)

            await async_loop.sock_sendall(client, b"-hellow-")
            client.close()

    async def periodic_ping(self) -> None:
        """
        periodically sends out pings (to itself, technically)
        """
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

            finally:
                await sleep(
                    PING_INTERVAL.second
                    + PING_INTERVAL.minute * 60
                    + PING_INTERVAL.hour * 3600
                )
                client.close()

    async def run(self) -> None:
        await gather(
            self.accept_ping(),
            self.periodic_ping()
        )

    def close(self) -> None:
        self.running = False


if __name__ == "__main__":
    pp = PingPong()
    signal.signal(signal.SIGINT, lambda *_: pp.close())
    signal.signal(signal.SIGTERM, lambda *_: pp.close())

    loop = new_event_loop()
    set_event_loop(loop)
    loop.run_until_complete(pp.run())
    pp.close()

import asyncio
import os
import socket
from typing import List

import uvicorn


def _make_ipv4_socket(port: int) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", port))
    sock.listen(2048)
    sock.setblocking(False)
    return sock


def _make_ipv6_socket(port: int) -> socket.socket | None:
    if not socket.has_ipv6:
        return None
    sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
    except OSError:
        pass
    try:
        sock.bind(("::", port))
    except OSError:
        sock.close()
        return None
    sock.listen(2048)
    sock.setblocking(False)
    return sock


def _build_sockets(port: int) -> List[socket.socket]:
    sockets: List[socket.socket] = [_make_ipv4_socket(port)]
    sock6 = _make_ipv6_socket(port)
    if sock6 is not None:
        sockets.append(sock6)
    return sockets


async def _serve() -> None:
    port = int(os.getenv("PORT", "8088"))
    config = uvicorn.Config("backend.apps.api.main:app", host=None, port=port)
    server = uvicorn.Server(config)
    sockets = _build_sockets(port)
    await server.serve(sockets=sockets)


if __name__ == "__main__":
    asyncio.run(_serve())

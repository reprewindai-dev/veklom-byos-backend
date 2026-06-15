import asyncio, socket, uvicorn
async def app(scope, receive, send):
    assert scope['type'] == 'http'
    await send({'type': 'http.response.start', 'status': 200, 'headers': [[b'content-type', b'text/plain']]})
    await send({'type': 'http.response.body', 'body': b'Hello, world!'})

if __name__ == '__main__':
    sock4 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock4.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock4.bind(('127.0.0.1', 9998))
    sock4.listen(1)
    sock4.setblocking(False)

    sock6 = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    sock6.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock6.bind(('::1', 9998))
    sock6.listen(1)
    sock6.setblocking(False)

    config = uvicorn.Config(app, host=None, port=9998)
    server = uvicorn.Server(config)
    asyncio.run(server.serve(sockets=[sock4, sock6]))
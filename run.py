import websockets, asyncio, re, signal


CHANNELS = {}

PORT = 8000
SERVER_URL = "localhost"
async def app():
    loop = asyncio.get_running_loop()
    stop = loop.create_future()
    try: loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)
    except: pass  # Ignoring error for Windows users with no SIGTERM
    print(f"Running service at : ws://{SERVER_URL}:{PORT}/")
    async with websockets.serve(lambda x: WebsocketNewConnectionsManager(x, loop), SERVER_URL, PORT):
        await stop


async def WebsocketNewConnectionsManager(connection, loop):
    # An user can subscribe to multiple different channels by using the syntax {url_ws_server}/CHNAME1/CHNAME2/...
    # The simple regex for url path is :
    regx = r"/(?:([a-zA-Z]+))"
    CHANNEL_NAMES = [el.lower() for el in re.findall(regx, connection.path)]
    
    if len(CHANNEL_NAMES) >= 1:
        try:
            for CHANNEL_NAME in CHANNEL_NAMES:
                if not CHANNEL_NAME in CHANNELS.keys():
                    CHANNELS[CHANNEL_NAME] = set()
                    loop.create_task(WebsocketClientWorker(CHANNEL_NAME))
                CHANNELS[CHANNEL_NAME].add(connection)
                print(f"Added a new Client({connection.id}) to Channel({CHANNEL_NAME})")
            await connection.wait_closed()

        finally:
            for CHANNEL_NAME in CHANNEL_NAMES:
                CHANNELS[CHANNEL_NAME].remove(connection)
                print(f"Removing Client({connection.id}) from Channel({CHANNEL_NAME})")
                if len(CHANNELS[CHANNEL_NAME]) == 0:
                    CHANNELS.pop(CHANNEL_NAME, None)
                    print(f"Destructing Channel({CHANNEL_NAME})")
    else:
        await connection.send("You are not correctly subscribed to a channel")
        await connection.close()


async def WebsocketClientWorker(CHANNEL_NAME):
    # Define your own Websocket Client url depending on the channel name
    url = f'wss://yourwebsocketclienturl.com/{CHANNEL_NAME}'
    print(f"Creating a new channel mirroring @ {url}")
    async with websockets.connect(url) as client:
        while CHANNEL_NAME in CHANNELS.keys():
            async for message_rcv in client:
                try:
                    websockets.broadcast(CHANNELS[CHANNEL_NAME], message_rcv)
                    nClients = len(CHANNELS[CHANNEL_NAME])
                    if nClients == 0: client.close()
                    print(f"-> Worker({CHANNEL_NAME}) pushed data to {nClients} clients")
                except Exception as e:
                    print("-> An error occured : ", e); break




asyncio.run(app())

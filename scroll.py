#!/usr/bin/python

import asyncio
from struct import Struct

from aiohttp import web
from evdev import UInput
from evdev import ecodes as e

HTML = """
<!doctype html>
<html>
<head>
    <meta charset=utf-8>
    <meta name=viewport content="width=device-width">
    <style>
        html, body { height: 100%; margin: 0 }
        body { display: flex; align-items: center; justify-content: center; background: black; user-select: none }
        #st { color: white; font-size: 20vw }
        #fs { position: fixed; top: 15px; right: 15px; border: none; background: none; color: white; font-size: 5vw }
    </style>
</head>
<body>
    <div id=st>⚠</div>
    <button id=fs>⛶</button>
    <script>
        fs.onclick = () =>
            document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen();

        let ws;
        function connect() {
            ws = new WebSocket('ws://' + location.host + '/ws');
            ws.onopen = () => { st.innerText = '' };
            ws.onclose = () => { st.innerText = '⚠'; setTimeout(connect, 1000) };
            ws.onerror = () => ws.close();
        }
        connect();

        let lastY = null, pending = 0;
        const buf = new Float32Array(1);

        document.addEventListener('touchstart', e => {
            if (e.touches.length === 1) lastY = e.touches[0].clientY;
        });

        document.addEventListener('touchmove', e => {
            e.preventDefault();
            if (lastY !== null && e.touches.length === 1 && ws.readyState === 1) {
                pending += e.touches[0].clientY - lastY;
                lastY = e.touches[0].clientY;
                if (ws.bufferedAmount === 0) {
                    buf[0] = pending;
                    pending = 0;
                    ws.send(buf.buffer);
                }
            }
        }, {passive: false});

        document.addEventListener('touchend', () => { lastY = null; pending = 0 });
    </script>
</body>
</html>
"""

ui = UInput({e.EV_REL: [e.REL_WHEEL_HI_RES], e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT]}, name="wifi-scroll")
print("Virtual device:", ui.name)


async def index(_req: web.Request) -> web.Response:
    return web.Response(text=HTML, content_type="text/html", headers={"Cache-Control": "no-store"})


_float = Struct("<f")


async def ws_handler(req: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse(compress=False)
    await ws.prepare(req)
    acc = 0.0
    try:
        async for msg in ws:
            acc += _float.unpack(msg.data)[0] * 6
            if ticks := int(acc):
                ui.write(e.EV_REL, e.REL_WHEEL_HI_RES, ticks)
                ui.syn()
                acc -= ticks
    except asyncio.CancelledError:
        pass
    return ws


app = web.Application()
app.add_routes([web.get("/", index), web.get("/ws", ws_handler)])
try:
    web.run_app(app, port=12687, print=None, access_log=None)
except KeyboardInterrupt:
    pass
finally:
    ui.close()

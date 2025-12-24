#!/usr/bin/python

from aiohttp import web
from evdev import UInput, ecodes as e

HTML_CONTENT = '''
<html>
    <body>
        <div id='status'>⚠</div>
        <button id='fs-btn'>⛶</button>
    </body>
    <style>
        body {
          display: flex;
          align-items: center;
          justify-content: center;
          margin: 0;
          height: 100%;
          background: black;
        }
        #status {
          color: white;
          font-size: 20vw;
        }
        #fs-btn {
          position: fixed;
          top: 15px;
          right: 15px;
          border: none;
          background: none;
          color: white;
          font-size: 5vw;
          line-height: 1;
        }
    </style>
    <script>
        document.getElementById('fs-btn').addEventListener('click', () => {
            document.fullscreenElement
                ? document.exitFullscreen()
                : document.documentElement.requestFullscreen();
        });

        const status = document.getElementById('status');

        let ws = new WebSocket('ws://' + location.host + '/ws');
        ws.onopen = () => { status.innerText = ''; };
        ws.onclose = () => { status.innerText = '⚠'; };
        ws.onerror = () => { ws.close(); }

        let lastY = null;

        document.addEventListener('touchstart', (e) => {
            if (e.touches.length === 1)
                lastY = e.touches[0].clientY;
        }, {passive: false});

        document.addEventListener('touchmove', (e) => {
            e.preventDefault();
            if (e.touches.length === 1 && lastY !== null) {
                if (ws.readyState === WebSocket.OPEN)
                    ws.send(e.touches[0].clientY - lastY);
                lastY = e.touches[0].clientY;
            }
        }, {passive: false});

        document.addEventListener('touchend', () => { lastY = null; });
    </script>
</html>
'''

ui = UInput({ e.EV_REL: [e.REL_WHEEL_HI_RES], e.EV_KEY: [e.BTN_LEFT, e.BTN_RIGHT] }, name='wifi-scroll')
print('Virtual device: ', ui.name)

async def index(request):
    return web.Response(text=HTML_CONTENT, content_type='text/html')

async def ws_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    acc = 0.
    async for msg in ws:
        acc += float(msg.data) * 6
        ia = int(acc)
        if ia != 0:
            ui.write(e.EV_REL, e.REL_WHEEL_HI_RES, ia)
            acc -= ia
        ui.syn()
    return ws

app = web.Application()
app.add_routes([web.get('/', index), web.get('/ws', ws_handler)])
web.run_app(app, port=12687, print=None)

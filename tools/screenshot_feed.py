"""Feeds the REAL Jervis window over its own WebSocket protocol, so the website's screenshots show the actual UI.

Every Jervis reply is produced by Jervis's own modules (equations, graphs, planets, earth); only the spoken user commands
are examples, taken from README.md and the window's "Try saying" list. Nothing listens to a microphone or calls an AI.

    venv/bin/python website/tools/screenshot_feed.py        (from the app folder; serves ws://localhost:8799/<scene>)

Then open the app's index.html in a browser as  index.html?ws=ws://localhost:8799/<scene>  where <scene> is chat, worksheet,
graph, globe or planet (the page needs a small window.require shim for 'electron' outside Electron), and take the screenshot.
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import equations  # noqa: E402
import graphs  # noqa: E402
import planets  # noqa: E402
import earth  # noqa: E402
import websockets  # noqa: E402

STATS = {"type": "system_stats", "data": {"cpu": 18, "ram": 57, "battery": 86}}
WEATHER = {"type": "weather", "data": {"city": "Ramat Gan, Israel", "temp": 27, "condition": "Clear sky"}}


def graph_payload(cmd):
    req = graphs.parse_request(cmd)
    info = graphs.build_function(req["ast"])
    return info, graphs.describe_function(info)


def globe_payload(cmd):
    req = earth.parse_request(cmd)
    info = earth.build(earth.geocode(req["a"]), earth.geocode(req["b"]))
    return info, earth.describe(info)


def planet_payload(cmd):
    req = planets.parse_request(cmd)
    info = planets.build(req["body"])
    return info, info["text"]


async def send(ws, obj):
    await ws.send(json.dumps(obj))
    await asyncio.sleep(0.05)


async def handler(ws):
    scene = ws.request.path.strip("/") or "chat"
    for m in (STATS, WEATHER):
        await send(ws, m)
    for cpu in (14, 21, 17, 26, 19, 23, 31, 22, 18, 24, 20, 18):
        await send(ws, {"type": "system_stats", "data": {"cpu": cpu, "ram": 57, "battery": 86}})

    if scene == "chat":
        eq_cmd = "Solve x squared minus 5x plus 6 equals 0"
        solved = equations.solve(*equations.parse_request(eq_cmd))
        await send(ws, {"sender": "user", "text": eq_cmd})
        await send(ws, {"sender": "jervis", "text": solved})
        p_cmd = "Tell me about Saturn"
        info, text = planet_payload(p_cmd)
        await send(ws, {"sender": "user", "text": p_cmd})
        await send(ws, {"sender": "jervis", "text": text})
        await send(ws, {"status": "listening"})
    elif scene == "worksheet":
        eq_cmd = "Solve x squared minus 5x plus 6 equals 0"
        await send(ws, {"sender": "user", "text": eq_cmd})
        await send(ws, {"sender": "jervis", "text": equations.solve(*equations.parse_request(eq_cmd))})
        await send(ws, {"status": "speaking"})
    elif scene == "graph":
        cmd = "Graph sine of x over x"
        info, text = graph_payload(cmd)
        await send(ws, {"sender": "user", "text": cmd})
        await send(ws, {"type": "graph", "data": info})
        await send(ws, {"sender": "jervis", "text": text})
        await send(ws, {"status": "speaking"})
    elif scene == "globe":
        cmd = "What is the distance between New York and Tel Aviv"
        info, text = globe_payload(cmd)
        await send(ws, {"sender": "user", "text": cmd})
        await send(ws, {"type": "globe", "data": info})
        await send(ws, {"sender": "jervis", "text": text})
        await send(ws, {"status": "speaking"})
    elif scene == "planet":
        cmd = "Tell me about Saturn"
        info, text = planet_payload(cmd)
        await send(ws, {"sender": "user", "text": cmd})
        await send(ws, {"type": "planet", "data": info})
        await send(ws, {"sender": "jervis", "text": text})
        await send(ws, {"status": "speaking"})
    await ws.wait_closed()


async def main():
    async with websockets.serve(handler, "localhost", 8799, max_size=40 * 1024 * 1024):
        print("demo feed on ws://localhost:8799", flush=True)
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())

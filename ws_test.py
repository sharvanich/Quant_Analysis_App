import websocket, json

def on_open(ws):
    print("✅ Connected to WS")

def on_message(ws, message):
    print("📩 Message:", message)

def on_error(ws, error):
    print("❌ Error:", error)

def on_close(ws, code, reason):
    print("🔒 Closed:", code, reason)

url = "ws://127.0.0.1:8000/api/v1/ws/live/btcusdt"  # note the symbol
ws = websocket.WebSocketApp(url, on_open=on_open, on_message=on_message, on_error=on_error, on_close=on_close)
ws.run_forever()

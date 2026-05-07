from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/test")
async def websocket_test(ws: WebSocket):
    await ws.accept()

    try:
        while True:
            data = await ws.receive_text()
            await ws.send_json({
                "received": data,
                "status": "working",
            })
    except WebSocketDisconnect:
        return

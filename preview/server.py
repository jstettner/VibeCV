from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pathlib import Path
from time import sleep
from PIL import Image
import io

FRAME_PATH = Path("/frames/demo.jpg")   # shared tmpfs / volume
app = FastAPI()

def mjpeg():
    while True:
        if FRAME_PATH.exists():
            with Image.open(FRAME_PATH) as im:
                buf = io.BytesIO()
                im.save(buf, format="JPEG", quality=80)
            yield (b"--frame\r\n"
                   b"Content-Type: image/jpeg\r\n\r\n" +
                   buf.getvalue() + b"\r\n")
        sleep(0.04)   # ~25 fps max (adjust)

@app.get("/stream")
def stream():
    return StreamingResponse(mjpeg(),
        media_type="multipart/x-mixed-replace; boundary=frame")


# Loops a local demo.mp4 forever and streams it to MediaMTX
# via RTSP (could be RTMP/SRT—just change the CMD line).

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive \
    FFREPORT=file=/dev/stdout:level=32

# -- 1. Fetch tiny static FFmpeg build (~7 MB)
# RUN apt-get update && apt-get install -y curl ca-certificates && \
#     curl -L -o /usr/local/bin/ffmpeg \
#       https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz && \
#     tar -xf /usr/local/bin/ffmpeg --strip-components=2 -C /usr/local/bin ffmpeg*/ffmpeg && \
#     chmod +x /usr/local/bin/ffmpeg && \
#     apt-get purge -y curl && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

# -- 2. Copy the sample clip (or mount your own at runtime)
COPY demo.mp4 /demo/demo.mp4

WORKDIR /demo

# -- 3. Loop & push
#   -re             → real-time
#   -stream_loop -1 → infinite loop
CMD ["sh", "-c", "ffmpeg -re -stream_loop -1 -i /demo/demo.mp4 \
                 -r $FPS -c:v libx264 -preset veryfast -tune zerolatency \
                 -pix_fmt yuv420p -f rtsp $MEDIAMTX_URL"]
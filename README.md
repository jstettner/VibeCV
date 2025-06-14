# Ambral

## Run the project

1. Install docker desktop

2. Start the docker images

```bash
docker compose up -d
```

## Stream from an iPhone

Download Streamcast Pro from the app store.

Find your LAN ip address (wifi or ethernet).

Something like

```bash
ipconfig getifaddr en0
```

Add a config in Streamcast Pro with the url `rtmp://<ip you found>:1935/live/iphone`

Start streaming on the same LAN (or set up port forwarding and auth on a server).

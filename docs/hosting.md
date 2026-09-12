# Hosting

The app runs as the Docker image on the developer's Mac. Tailscale makes it reachable from the
phone anywhere, without exposing anything to the public internet. This beats a cloud VM: it costs
nothing, and Stockfish will run on the Mac's CPU later.

## One-time setup

1. Install Tailscale on the Mac, from tailscale.com/download.
2. Install Tailscale on the iPhone, from the App Store.
3. Sign both into the same tailnet.
4. Enable MagicDNS in the Tailscale admin console. It is on by default for new tailnets.
5. Confirm the Mac's Tailscale name with `tailscale status`. The machine is named
   `clements-macbook-air`; MagicDNS names are lowercase.

## Run

After `docker build` (see docs/README.md):

```
docker run -d --restart unless-stopped --name chess-review -p 8000:8000 -v chess-review-data:/data chess-review
```

`--restart unless-stopped` brings the container back after Docker Desktop restarts. Open
`http://clements-macbook-air:8000` on the phone.

Docker Desktop must be running and the Mac must be awake. When plugged in, enable System
Settings > Battery > "Prevent automatic sleeping when the display is off".

## Update

```
git pull
docker build -t chess-review .
docker rm -f chess-review
docker run -d --restart unless-stopped --name chess-review -p 8000:8000 -v chess-review-data:/data chess-review
```

The named volume keeps the games across rebuilds.

## Limits

- Traffic goes over Tailscale's encrypted mesh only; nothing listens on the public internet.
- There is no authentication in the app itself, so anyone on the tailnet can use it. That is fine
  for a single-user tailnet.

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
docker run -d --restart unless-stopped --name chess-review -p 8000:8000 \
  -v ~/Downloads/chess-analysis:/data -e CHESS_REVIEW_DB=/data/analysis.sqlite3 chess-review
```

`--restart unless-stopped` brings the container back after Docker Desktop restarts. Open
`http://clements-macbook-air:8000` on the phone.

The container uses the same SQLite file as the analysis scripts on the Mac,
`~/Downloads/chess-analysis/analysis.sqlite3`, so there is one database with every game and
analysis. The first start triggers a macOS prompt for Docker to access the Downloads folder;
allow it, or the container stays in `Created`.

Don't run a second server on the same file while the container runs. SQLite's locking is not
reliable between the Mac and Docker's Linux VM. To try a branch locally, point
`CHESS_REVIEW_DB` at a copy made with `sqlite3 <file> ".backup <copy>"`.

Docker Desktop must be running and the Mac must be awake. When plugged in, enable System
Settings > Battery > "Prevent automatic sleeping when the display is off".

## Update

```
git pull
docker build -t chess-review .
docker rm -f chess-review
docker run -d --restart unless-stopped --name chess-review -p 8000:8000 \
  -v ~/Downloads/chess-analysis:/data -e CHESS_REVIEW_DB=/data/analysis.sqlite3 chess-review
```

The database lives on the Mac, so rebuilds keep every game and analysis.

## Limits

- Traffic goes over Tailscale's encrypted mesh only; nothing listens on the public internet.
- There is no authentication in the app itself, so anyone on the tailnet can use it. That is fine
  for a single-user tailnet.

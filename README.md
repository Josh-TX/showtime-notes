Showtime Notes

this is still in-progress. 

## Microphone access / HTTPS

Browsers only allow microphone/tab capture in a secure context (https or `localhost`). A plain `http://<lan-ip>` page can't become the listener. Options:

- Open the page via `http://localhost:8000` on the server machine.
- Run uvicorn with TLS: `uvicorn app.main:app --host 0.0.0.0 --port 8443 --ssl-keyfile key.pem --ssl-certfile fullchain.pem`. Needs a cert trusted by the browser, e.g. Let's Encrypt (DNS-01, e.g. a DuckDNS name pointing at the LAN IP) or mkcert.
- Put a reverse proxy (Caddy, nginx) in front. It must forward WebSocket upgrades on `/ws`.

The client picks `wss://` automatically on https pages.

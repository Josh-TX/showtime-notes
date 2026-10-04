# Showtime Notes

Record a song's rehearsal, add notes to a timeline, and during the live performance the timeline will stay in sync. 

# Usage

3 ways to run showtime-notes

1. **Release zip:** download a release, unzip it, and in the folder run `uv run showtime-notes [--port <port>] [--data <dir>]`. Then open http://localhost:8000.
2. **Development:** clone this repo, `npm ci` in `frontend/`, `uv sync` in `backend/`, then run the "Full Stack" launch config in VS Code. Open the Vite dev server at http://localhost:5173 (proxies `/api` and `/ws` to the backend on 8000).
3. **From source, no VS Code:** clone this repo, then:

       cd frontend && npm ci && npm run build   # outputs to backend/app/static
       cd ../backend && uv run showtime-notes

   The backend serves the built frontend at http://localhost:8000.

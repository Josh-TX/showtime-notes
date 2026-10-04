import argparse
import os


def main() -> None:
    parser = argparse.ArgumentParser(prog="showtime-notes", description="Run the Showtime Notes server")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    parser.add_argument("--data", help="data directory (default: SHOWTIME_DATA or ./data next to app/)")
    args = parser.parse_args()

    if args.data:
        os.environ["SHOWTIME_DATA"] = args.data

    import uvicorn

    from .main import app

    uvicorn.run(app, host="0.0.0.0", port=args.port)

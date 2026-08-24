"""Download Open-Meteo archive observations into data/raw."""
from __future__ import annotations
import argparse
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--latitude", required=True, type=float); parser.add_argument("--longitude", required=True, type=float)
    parser.add_argument("--start-date", required=True); parser.add_argument("--end-date", required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "data/raw/openmeteo.csv")
    args = parser.parse_args(); args.output.parent.mkdir(parents=True, exist_ok=True)
    query = urlencode({"latitude": args.latitude, "longitude": args.longitude, "start_date": args.start_date,
                       "end_date": args.end_date, "hourly": "temperature_2m,relative_humidity_2m,surface_pressure",
                       "timezone": "UTC", "format": "csv"})
    url = "https://archive-api.open-meteo.com/v1/archive?" + query
    with urlopen(Request(url, headers={"User-Agent": "SkyGuard-AI-Phase1/1.0"}), timeout=60) as response:
        args.output.write_bytes(response.read())
    print(f"Downloaded {url} to {args.output}")

if __name__ == "__main__": main()

"""Download a Meteostat bulk hourly station archive into data/raw."""
from __future__ import annotations
import argparse, gzip, shutil
from pathlib import Path
from urllib.request import Request, urlopen

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--station", required=True, help="Meteostat station identifier")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or Path(__file__).resolve().parents[1] / "data/raw" / f"meteostat_{args.station}.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://bulk.meteostat.net/v2/hourly/{args.station}.csv.gz"
    request = Request(url, headers={"User-Agent": "SkyGuard-AI-Phase1/1.0"})
    with urlopen(request, timeout=60) as response, gzip.GzipFile(fileobj=response) as source, output.open("wb") as target:
        shutil.copyfileobj(source, target)
    print(f"Downloaded {url} to {output}")

if __name__ == "__main__": main()

"""Marketplace-Aufrufe gegen die laufende API demonstrieren, ohne Zusatzpakete."""

import argparse
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

MOCK_DATA = Path(__file__).resolve().parent.parent / "mock-data"


def call(
    base_url: str, method: str, path: str, *, expected: int,
    payload: dict | None = None,
) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload else None
    request = Request(
        base_url + path, data=body, method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            code, raw = response.status, response.read()
            location = response.headers.get("Location")
    except HTTPError as error:
        with error:
            code, raw = error.code, error.read()
        location = None
    except URLError as error:
        raise SystemExit(
            f"API unter {base_url} nicht erreichbar: {error.reason}\n"
            "Zuerst den Server gemäß README starten."
        ) from error
    result = json.loads(raw)
    print(f"\n{method} {path} -> {code}")
    if location:
        print(f"Location: {location}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if code != expected:
        raise SystemExit(f"Erwartet: HTTP {expected}; erhalten: HTTP {code}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    call(base_url, "GET", "/health", expected=200)
    for filename in ("amazon-return.json", "zalando-return.json"):
        payload = json.loads((MOCK_DATA / filename).read_text(encoding="utf-8"))
        created = call(base_url, "POST", "/api/v1/returns", expected=201, payload=payload)
        call(base_url, "GET", f"/api/v1/returns/{created['id']}", expected=200)
    query = urlencode({"marketplace": "amazon", "limit": 5, "offset": 0})
    call(base_url, "GET", f"/api/v1/returns?{query}", expected=200)
    invalid = json.loads((MOCK_DATA / "invalid-return.json").read_text(encoding="utf-8"))
    call(base_url, "POST", "/api/v1/returns", expected=422, payload=invalid)
    call(
        base_url, "GET", "/api/v1/returns/00000000-0000-0000-0000-000000000000",
        expected=404,
    )
    print("\nDemonstration abgeschlossen. Zwei neue Anmeldungen wurden gespeichert.")


if __name__ == "__main__":
    main()

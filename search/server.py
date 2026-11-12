"""Serve the QUARCS image's sky catalogs through the original web search API."""

import json
import re
from pathlib import Path
from socketserver import ThreadingMixIn
from unicodedata import normalize
from urllib.parse import parse_qs
from wsgiref.simple_server import WSGIServer, make_server


CATALOG_DIR = Path(__file__).resolve().parent
PLANETS = (
    "Sun Mercury Venus Moon Earth Mars Io Europa Ganymede Callisto Jupiter "
    "Mimas Enceladus Tethys Dione Rhea Titan Hyperion Iapetus Atlas Pan Saturn "
    "Ariel Umbriel Titania Oberon Miranda Uranus Neptune Pluto"
).split()
MINOR_PLANETS = (
    "Eris Makemake Haumea Sedna Orcus Quaoar Vesta Ceres Varda Varuna Ixion "
    "Dziewanna Salacia Pallas Lempo Chaos Huya Eunomia Sila-Nunam Juno Hygiea "
    "Iris Altjira Praamzius Hebe Chiron Teharonhiawako Herculina Amphitrite "
    "Psyche Borasisi Dembowska Interamnia Laetitia Davida Metis Irene"
).split()


def normalize_name(name):
    name = normalize("NFKC", name).casefold().strip()
    return re.sub(r"\s+", "", name.removeprefix("name "))


def catalog_sources():
    for filename, model, kind in (("dso.txt", "dso", "dso"), ("stars_l.txt", "star", "*")):
        with (CATALOG_DIR / filename).open(encoding="utf-8") as catalog:
            for line in catalog:
                ra, dec, aliases = line.strip().split("--", 2)
                yield aliases.split("|"), model, kind, float(ra), float(dec)
    for names, model, kind in ((PLANETS, "SSO", "SSO"), (MINOR_PLANETS, "mpc_asteroid", "MPl")):
        for name in names:
            # Stellarium computes the position of moving targets for the observer's time.
            yield [f"NAME {name}"], model, kind, None, None


def build_index():
    sources = []
    index = []
    exact = {}
    for names, model, kind, ra, dec in catalog_sources():
        source_id = len(sources)
        sources.append({
            "model": model,
            "model_data": {"ra": ra, "de": dec},
            "coordinate_unit": "rad",
            "names": names,
            "short_name": names[0],
            "types": [kind],
        })
        for name in names:
            key = normalize_name(name)
            if key:
                index.append((key, name, source_id))
                exact.setdefault(key, (name, source_id))

    localized_catalog = CATALOG_DIR / "sky-zh-cn.json"
    if localized_catalog.is_file():
        catalog = json.loads(localized_catalog.read_text(encoding="utf-8"))
        for entry in catalog["objects"]:
            match = next((exact[key] for name in entry["names"]
                          if (key := normalize_name(name)) in exact), None)
            if match is None:
                continue
            _, source_id = match
            for alias in (entry["zh"], *entry.get("aliases", [])):
                key = normalize_name(alias)
                if key and key not in exact:
                    index.append((key, alias, source_id))
                    exact[key] = (alias, source_id)
    return sources, index, exact


SOURCES, INDEX, EXACT = build_index()


def search(query, limit):
    key = normalize_name(query)
    if not key:
        return []
    matches = []
    for alias, name, source_id in INDEX:
        position = alias.find(key)
        if position >= 0:
            matches.append((position, len(alias), alias, name, source_id))
    results = []
    seen = set()
    for _, _, _, name, source_id in sorted(matches):
        if source_id not in seen:
            seen.add(source_id)
            results.append(dict(SOURCES[source_id], match=name))
            if len(results) == limit:
                break
    return results


def application(environ, start_response):
    path = environ["PATH_INFO"]
    status = "200 OK"
    if environ["REQUEST_METHOD"] != "GET":
        status, result = "405 Method Not Allowed", {"error": "GET required"}
    elif path == "/":
        query_string = environ["QUERY_STRING"]
        try:
            args = parse_qs(query_string, max_num_fields=16)
        except ValueError:
            args = {}
            status = "400 Bad Request"
        query = args.get("q", [""])[0][:120]
        try:
            limit = min(30, max(1, int(args.get("limit", ["10"])[0])))
        except ValueError:
            limit = 10
        result = search(query, limit)
        if not result and "+" in query_string and args:
            # The original browser concatenates catalog names such as MCG+07-02-016 into the URL.
            query = parse_qs(query_string.replace("+", "%2B")).get("q", [""])[0][:120]
            result = search(query, limit)
    elif path.startswith("/name/"):
        name = path[len("/name/"):].encode("latin-1").decode("utf-8", errors="replace")
        match = EXACT.get(normalize_name(name))
        if match:
            alias, source_id = match
            result = dict(SOURCES[source_id], match=alias)
        else:
            status, result = "404 Not Found", {"error": "Unknown sky source"}
    else:
        status, result = "404 Not Found", {"error": "Unknown route"}

    body = json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    start_response(status, [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(body))),
    ])
    return [body]


class SearchServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


if __name__ == "__main__":
    with make_server("127.0.0.1", 18090, application, server_class=SearchServer) as server:
        print(f"Loaded {len(SOURCES)} sky sources and {len(INDEX)} names", flush=True)
        server.serve_forever()

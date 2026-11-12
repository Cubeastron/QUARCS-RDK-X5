"""Route Western constellation and selected deep-sky labels through the translator."""

import json
import re
import sys
from pathlib import Path


source, destination = map(Path, sys.argv[1:])
culture = json.loads(source.read_text(encoding="utf-8"))
if culture["id"] != "western":
    raise ValueError("Expected the Western sky culture")

# The Web Engine defaults to English internally and renders preferred native
# names without consulting translateFn. Latin names uniquely identify all 88
# constellations and are already the English display names for this culture.
culture["langs_use_native_names"] = []
for constellation in culture["constellations"]:
    name = constellation["common_name"]
    name["english"] = name["native"]

# The engine uses the first designation of each deep-sky object as the key.
# Register its known identifiers and common names so a shorter catalog number
# does not win over the localized label in the engine's default label selection.
catalog_path = Path(__file__).resolve().parents[1] / "web/src/assets/sky-zh-cn.json"
catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
common_names = culture.setdefault("common_names", {})
for entry in catalog["objects"]:
    label = entry.get("canvasLabel")
    if not label:
        continue
    for name in entry["names"]:
        if not name.startswith("NAME ") and not re.match(r"^(M|NGC|IC|C) \d", name):
            name = "NAME " + name
        common_names.setdefault(name, [{"english": label}])

destination.write_text(json.dumps(culture, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

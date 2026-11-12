"""Make the existing Western constellation labels go through the engine translator."""

import json
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

destination.write_text(json.dumps(culture, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

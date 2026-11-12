"""Subset the SC faces (index 2) of Noto Sans CJK Regular and Bold TTC files."""

import json
import sys
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont


web_dir = Path(__file__).resolve().parents[1]
catalog = json.loads((web_dir / "src/assets/sky-zh-cn.json").read_text(encoding="utf-8"))
glyphs = {ord(char) for char in json.dumps(catalog, ensure_ascii=False) if ord(char) > 127}

for weight, path in zip(("Regular", "Bold"), sys.argv[1:], strict=True):
    font = TTFont(path, fontNumber=2, recalcTimestamp=False)
    if "Noto Sans CJK SC" not in font["name"].getDebugName(1):
        raise ValueError(f"Expected the Simplified Chinese face in {path}")
    postscript_name = f"QUARCSSkySC-{weight}"
    font["name"].removeNames(nameID=20)
    for name_id, value in (
        (1, "QUARCS Sky SC"), (2, weight), (3, postscript_name),
        (4, f"QUARCS Sky SC {weight}"), (6, postscript_name),
        (16, "QUARCS Sky SC"), (17, weight),
    ):
        for record in font["name"].names:
            if record.nameID == name_id:
                record.string = value

    cff = font["CFF "].cff
    cff.fontNames[0] = postscript_name
    cff.topDictIndex[0].FullName = f"QUARCS Sky SC {weight}"
    cff.topDictIndex[0].FamilyName = "QUARCS Sky SC"

    options = subset.Options()
    options.name_IDs = ["*"]
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(unicodes=glyphs)
    subsetter.subset(font)
    if not glyphs <= font.getBestCmap().keys():
        raise ValueError(f"Some map labels are missing glyphs in {path}")
    font.save(web_dir / f"public/fonts/{postscript_name}.otf")

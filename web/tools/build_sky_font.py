"""Build static TrueType subsets from the Noto Sans SC variable font."""

import json
import sys
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont


web_dir = Path(__file__).resolve().parents[1]
catalog = json.loads((web_dir / "src/assets/sky-zh-cn.json").read_text(encoding="utf-8"))
glyphs = {ord(char) for char in json.dumps(catalog, ensure_ascii=False) if ord(char) > 127}

path, = sys.argv[1:]
for weight, axis in (("Regular", 400), ("Bold", 700)):
    font = TTFont(path, recalcTimestamp=False)
    if font["name"].getDebugName(16) != "Noto Sans SC" or "glyf" not in font:
        raise ValueError(f"Expected the Noto Sans SC variable TrueType font in {path}")

    options = subset.Options()
    options.name_IDs = ["*"]
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(unicodes=glyphs)
    subsetter.subset(font)
    instantiateVariableFont(font, {"wght": axis}, inplace=True, updateFontNames=True)
    if not glyphs <= font.getBestCmap().keys():
        raise ValueError(f"Some map labels are missing glyphs in {path}")

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

    font.save(web_dir / f"public/fonts/{postscript_name}.ttf")

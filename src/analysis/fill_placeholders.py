
import re, json
from pathlib import Path

def fill_placeholders(tex_in: str, json_map: str, tex_out: str):
    s = Path(tex_in).read_text(encoding="utf-8")
    mapping = json.loads(Path(json_map).read_text(encoding="utf-8"))
    for key, val in mapping.items():
        s = s.replace(key, str(val))
    Path(tex_out).write_text(s, encoding="utf-8")

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--tex_in", required=True)
    p.add_argument("--json_map", required=True)
    p.add_argument("--tex_out", required=True)
    a = p.parse_args()
    fill_placeholders(a.tex_in, a.json_map, a.tex_out)
    print("Wrote", a.tex_out)

#!/usr/bin/env python3
"""Turn the private masters into shareable collection files.

The private masters live in a SEPARATE private repo, by default the sibling
directory ../postdiluvian-private (override with $POSTDILUVIAN_PRIVATE):

  <private>/cocktails.json      full recipe list  (you edit this)
  <private>/ingredients.json    full vocabulary   (you edit this)

Writes  <private>/collection.full.json   whole collection, self-contained  (share by hand)
        data/collection.json             the public basics, self-contained (committed, served by Pages)

meta.version is a calendar string: "YYYY.MM.DD", or "YYYY.MM.DD.N" (N>=2) for the
Nth content change in one day. It only advances when that file's recipe/ingredient
content actually changes (compared via meta.contentHash).

If the private directory is missing (a bare clone of the public repo), this
no-ops and the committed data/collection.json is left as-is. Wired into
.githooks/pre-commit.
"""
import datetime
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PRIVATE = Path(os.environ.get("POSTDILUVIAN_PRIVATE", ROOT.parent / "postdiluvian-private"))
COCKTAILS = PRIVATE / "cocktails.json"
INGREDIENTS = PRIVATE / "ingredients.json"
FULL_OUT = PRIVATE / "collection.full.json"
PUBLIC_OUT = ROOT / "data" / "collection.json"

KIND = "postdiluvian-collection"
BASICS = ["martini", "negroni", "manhattan", "whiskey-sour", "daiquiri", "sidecar",
          "paper-plane", "brown-derby"]


def content_hash(coll):
    payload = json.dumps({
        "ingredients": sorted(coll["ingredients"], key=lambda i: i["id"]),
        "cocktails": sorted(coll["cocktails"], key=lambda c: c["id"]),
    }, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def next_version(prev, today):
    if not prev or not prev.startswith(today):
        return today
    if prev == today:
        return today + ".2"
    try:
        return "%s.%d" % (today, int(prev.rsplit(".", 1)[1]) + 1)
    except ValueError:
        return today + ".2"


def load(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def stamp(coll, name, extra_meta=None):
    today = datetime.date.today().isoformat().replace("-", ".")
    h = content_hash(coll)
    prev = (load(coll["_out"]) or {}).get("meta", {})
    changed = prev.get("contentHash") != h
    version = next_version(prev.get("version"), today) if changed else (prev.get("version") or today)
    meta = {"kind": KIND, "name": name, "version": version, "contentHash": h}
    if extra_meta:
        meta.update(extra_meta)
    coll["meta"] = meta
    return version, changed


def write(coll):
    out = coll.pop("_out")
    out.parent.mkdir(parents=True, exist_ok=True)
    ordered = {"meta": coll["meta"], "ingredients": coll["ingredients"], "cocktails": coll["cocktails"]}
    out.write_text(json.dumps(ordered, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    if not COCKTAILS.exists() or not INGREDIENTS.exists():
        print("publish: no private masters at %s — data/collection.json left as committed" % PRIVATE)
        return 0

    master = json.loads(COCKTAILS.read_text(encoding="utf-8"))
    cocktails = master["cocktails"]
    ingredients = json.loads(INGREDIENTS.read_text(encoding="utf-8"))["ingredients"]

    # Collection names are set in cocktails.json's meta block, so they survive a
    # regenerate. Edit meta.name / meta.publicName there, not in the output files.
    mmeta = master.get("meta", {})
    full_name = mmeta.get("name", "Postdiluvian — full collection")
    public_name = mmeta.get("publicName", "Postdiluvian — basics")

    full = {"_out": FULL_OUT, "ingredients": ingredients, "cocktails": cocktails}
    fv, fchg = stamp(full, full_name)
    write(full)

    picked = [c for c in cocktails if c["id"] in set(BASICS)]
    missing = set(BASICS) - {c["id"] for c in picked}
    if missing:
        print("publish: ERROR — basics not found in local/cocktails.json: " + ", ".join(sorted(missing)))
        return 1
    used = set()
    for c in picked:
        used.update(i["ref"] for i in c["ingredients"])
        used.update(c.get("base", []))
    pub = {
        "_out": PUBLIC_OUT,
        "ingredients": [i for i in ingredients if i["id"] in used],
        "cocktails": sorted(picked, key=lambda c: c["name"].lower()),
    }
    pv, pchg = stamp(pub, public_name,
                     {"note": "A public sample. The full collection is shared privately."})
    write(pub)

    # ---- starter master files: the same 8, split into the format the editor loads ----
    starter_ck = ROOT / "data" / "starter" / "cocktails.json"
    starter_ig = ROOT / "data" / "starter" / "ingredients.json"
    starter_ck.parent.mkdir(parents=True, exist_ok=True)
    starter_ck.write_text(json.dumps({
        "meta": {
            "name": "My cocktails",
            "publicName": "My cocktails — sample",
            "mlPerOz": 30,
            "note": "Starter master file: the 8 classics from Postdiluvian's public sample. "
                    "Edit freely — this is yours. Pair it with ingredients.json in this folder.",
        },
        "cocktails": sorted(picked, key=lambda c: c["name"].lower()),
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    starter_ig.write_text(json.dumps({
        "meta": {
            "note": "Starter vocabulary — only the ingredients the sample cocktails use. Add your own.",
            "categories": ["spirit", "vermouth", "fortified", "wine", "liqueur", "amaro",
                           "bitters", "juice", "syrup", "other"],
            "families": ["gin", "whiskey", "rum", "agave", "brandy", "vodka", "aquavit", "other"],
            "mlPerOz": 30,
        },
        "ingredients": [i for i in ingredients if i["id"] in used],
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("publish: full v%s (%d recipes)%s   public v%s (%d recipes)%s   + starter (%d)" % (
        fv, len(cocktails), "  [changed]" if fchg else "",
        pv, len(picked), "  [changed]" if pchg else "", len(picked)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

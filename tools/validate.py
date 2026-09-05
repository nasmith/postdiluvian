#!/usr/bin/env python3
"""Validate a Postdiluvian collection file ({ meta, ingredients, cocktails }).

No third-party deps. Exit 0 = clean, 1 = errors. Warnings never fail.

  python3 tools/validate.py                     # checks data/collection.json
  python3 tools/validate.py local/collection.full.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

METHODS = {"shake", "dry-shake", "stir", "build", "swizzle", "blend", "throw"}
GLASSES = {"coupe", "old-fashioned", "rocks", "nick-and-nora", "flute", "collins", "highball", "wine"}
SERVICE = {"up", "rocks", "long", "neat"}
ICE = {"none", "large-cube", "cubed", "crushed"}
UNITS = {"dash", "drops", "tsp", "barspoon", "piece", "rinse", "top", "leaves", "sprig"}
CATEGORIES = {"spirit", "vermouth", "fortified", "wine", "liqueur", "amaro", "bitters", "juice", "syrup", "other"}
FAMILIES = {"gin", "whiskey", "rum", "agave", "brandy", "vodka", "aquavit", "other", None}
BASE_CATS = {"spirit", "amaro", "fortified", "liqueur", "wine"}


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "collection.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    errors, warnings = [], []
    e, w = errors.append, warnings.append

    meta = doc.get("meta") or {}
    if meta.get("kind") != "postdiluvian-collection":
        e("meta.kind must be \"postdiluvian-collection\"")
    if not meta.get("version"):
        w("meta.version is missing")

    ing = doc.get("ingredients")
    ckt = doc.get("cocktails")
    if not isinstance(ing, list) or not isinstance(ckt, list):
        print("  ERROR ingredients and cocktails must both be arrays")
        return 1

    ids, alias_owner = set(), {}
    for it in ing:
        i = it["id"]
        if i in ids:
            e("ingredient duplicate id '%s'" % i)
        ids.add(i)
        if it.get("category") not in CATEGORIES:
            e("ingredient %s: bad category %r" % (i, it.get("category")))
        if it.get("family") not in FAMILIES:
            e("ingredient %s: bad family %r" % (i, it.get("family")))
        if it.get("category") == "spirit" and it.get("family") is None:
            e("ingredient %s: spirit needs a family" % i)
        for a in it.get("aliases", []):
            a = a.lower()
            if a == i:
                continue
            if a in ids:
                e("ingredient alias '%s' (%s) collides with an id" % (a, i))
            if a in alias_owner:
                e("ingredient alias '%s' shared by %s and %s" % (a, alias_owner[a], i))
            alias_owner[a] = i

    by_id = {it["id"]: it for it in ing}
    used, cids = set(), set()
    for c in ckt:
        cid = c["id"]
        if cid in cids:
            e("cocktail duplicate id '%s'" % cid)
        cids.add(cid)
        t = "cocktail[%s]" % cid
        if c.get("method") not in METHODS:
            e("%s: bad method %r" % (t, c.get("method")))
        if c.get("glass") not in GLASSES:
            e("%s: bad glass %r" % (t, c.get("glass")))
        if c.get("service") not in SERVICE:
            e("%s: bad service %r" % (t, c.get("service")))
        if c.get("ice") not in ICE:
            e("%s: bad ice %r" % (t, c.get("ice")))
        if c.get("status") not in ("active", "wishlist"):
            e("%s: bad status %r" % (t, c.get("status")))
        if not c.get("ingredients"):
            e("%s: no ingredients" % t)
        refs = {i["ref"] for i in c.get("ingredients", [])}
        for b in c.get("base", []):
            if b not in by_id:
                e("%s: base '%s' is not an ingredient id" % (t, b))
            elif by_id[b]["category"] not in BASE_CATS:
                w("%s: base '%s' has category %s" % (t, b, by_id[b]["category"]))
            if b not in refs:
                w("%s: base '%s' is not among its ingredients" % (t, b))
        vo = c.get("variantOf")
        if vo and vo not in cids and vo not in {x["id"] for x in ckt}:
            e("%s: variantOf '%s' not found" % (t, vo))
        for i in c.get("ingredients", []):
            used.add(i["ref"])
            if i["ref"] not in by_id:
                e("%s: ingredient ref '%s' not in this collection's vocabulary" % (t, i["ref"]))
            if "unit" in i and i["unit"] not in UNITS:
                e("%s: bad unit %r on %s" % (t, i["unit"], i["ref"]))
            if "ml" not in i and "unit" not in i and "amount" not in i:
                w("%s: %s has no ml / amount / unit" % (t, i["ref"]))
            if i.get("ml", 0) and i["ml"] > 180:
                w("%s: %s is %s ml — large pour, check" % (t, i["ref"], i["ml"]))

    for i in sorted(ids - used):
        w("ingredient '%s' is unused" % i)

    for m in warnings:
        print("  warn  " + m)
    for m in errors:
        print("  ERROR " + m)
    print("\n%s: %d cocktails, %d ingredients, %d errors, %d warnings"
          % (path.name, len(ckt), len(ing), len(errors), len(warnings)))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())

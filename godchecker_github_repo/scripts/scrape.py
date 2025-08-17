#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from pathlib import Path
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))

def iso(y, m, d, hh, mm):
    return datetime(y, m, d, hh, mm, tzinfo=JST).isoformat()

def build_sample():
    y = datetime.now(JST).year
    return [
        {
            "id": f"palace_{y}_sample",
            "title": "皇居外苑 周辺規制（サンプル）",
            "purpose": "来訪行事に伴う警備・安全確保",
            "desc": "周回道路の一部で一時通行止め。",
            "authority": "警視庁",
            "area": "千代田区 皇居外苑",
            "startAt": iso(y, 8, 20, 9, 0),
            "endAt":   iso(y, 8, 20, 12, 0),
            "geometry": { "type":"Polygon", "coordinates":[ [ [139.7605,35.6810],[139.7660,35.6810],[139.7660,35.6850],[139.7605,35.6850],[139.7605,35.6810] ] ] },
            "roads": ["内堀通り"],
            "tags": ["imperial"],
            "sourceUrl": "https://example.mpd.go.jp/palace_aug20"
        },
        {
            "id": f"pm_{y}_sample",
            "title": "首相官邸〜霞が関 周辺規制（サンプル）",
            "purpose": "内閣総理大臣の移動に伴う警護運用",
            "desc": "桜田通り・外堀通りの一部で断続的な交通制御。",
            "authority": "警視庁",
            "area": "千代田区 霞が関",
            "startAt": iso(y, 8, 26, 8, 0),
            "endAt":   iso(y, 8, 26, 9, 0),
            "geometry": { "type":"LineString", "coordinates":[ [139.7480,35.6735],[139.7528,35.6760],[139.7575,35.6765] ] },
            "roads": ["桜田通り","外堀通り"],
            "tags": ["pm"],
            "sourceUrl": "https://example.mpd.go.jp/pm_akasaka"
        },
        {
            "id": f"state_{y}_sample",
            "title": "迎賓館（赤坂離宮）周辺規制（サンプル）",
            "purpose": "国賓来日に伴う儀仗・護衛対応",
            "desc": "外苑東通りで一時通行止め、周辺で警備強化。",
            "authority": "警視庁",
            "area": "港区 元赤坂",
            "startAt": iso(y, 9, 10, 10, 0),
            "endAt":   iso(y, 9, 10, 13, 0),
            "geometry": { "type":"Polygon", "coordinates":[ [ [139.7248,35.6778],[139.7312,35.6778],[139.7312,35.6816],[139.7248,35.6816],[139.7248,35.6778] ] ] },
            "roads": ["外苑東通り"],
            "tags": ["state"],
            "sourceUrl": "https://example.mpd.go.jp/state_guest_akasaka"
        }
    ]

def merge_manual(base):
    out = {i["id"]: i for i in base}
    manu = Path("data/manual")
    if manu.exists():
        for p in manu.glob("*.json"):
            try:
                arr = json.loads(p.read_text(encoding="utf-8"))
                for it in arr:
                    out[it["id"]] = it
            except Exception:
                pass
    return list(out.values())

def main():
    items = build_sample()
    items = merge_manual(items)
    items.sort(key=lambda x: x.get("startAt",""))
    Path("web/restrictions.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote web/restrictions.json with {len(items)} items")

if __name__ == "__main__":
    main()

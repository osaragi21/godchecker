#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
God Checker – 自動収集スクリプト（公開情報ベース）
- 宮内庁（行事・ご日程の公表）
- 首相官邸（会見・日程の公表/動静）
- 外務省（国賓来日の発表・日程）
- （任意）警視庁/首都高の“公表済みの交通規制”告知

※ 公式サイトのHTMLは変わりやすいので、CSSセレクタは“ほどよく緩め”＋フォールバックを多段で用意。
※ すべて“公開情報の要約”のみを扱い、具体ルートの推測は行いません。
"""

from __future__ import annotations
import re, json, time, sys, math, html
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup

JST = timezone(timedelta(hours=9))

UA = "GodChecker/1.0 (+github actions; public info only)"
REQ_KW = dict(timeout=25, headers={"User-Agent": UA})

OUT_PATH = Path("docs/restrictions.json")  # ← GitHub Pages が /docs を配信

# ========= ユーティリティ =========

def jst_now() -> datetime:
    return datetime.now(JST)

def iso(dt_: datetime) -> str:
    if dt_.tzinfo is None:
        dt_ = dt_.replace(tzinfo=JST)
    return dt_.astimezone(JST).isoformat()

def parse_date_guess(text: str, default_time=(9, 0)) -> Optional[datetime]:
    """
    日本語の '2025年9月10日' / '9月10日' / '2025/09/10' / '9/10' などを緩く拾う。
    時刻が無い場合は default_time を採用。
    """
    t = text
    y = jst_now().year

    # 年月日（YYYY年M月D日）
    m = re.search(r"(?P<y>20\d{2})[年/\.-]\s*(?P<m>\d{1,2})[月/\.-]\s*(?P<d>\d{1,2})[日]?", t)
    if m:
        y2 = int(m.group("y"))
        m2 = int(m.group("m"))
        d2 = int(m.group("d"))
        return datetime(y2, m2, d2, default_time[0], default_time[1], tzinfo=JST)

    # 月日（M月D日）
    m = re.search(r"(?P<m>\d{1,2})[月/\.-]\s*(?P<d>\d{1,2})[日]?", t)
    if m:
        m2 = int(m.group("m"))
        d2 = int(m.group("d"))
        # 年が無ければ今年。既に過ぎていれば来年扱いに“しない”ほうが安全なので今年固定。
        return datetime(y, m2, d2, default_time[0], default_time[1], tzinfo=JST)

    # YYYY-MM-DD
    m = re.search(r"(?P<y>20\d{2})-(?P<m>\d{1,2})-(?P<d>\d{1,2})", t)
    if m:
        return datetime(int(m.group("y")), int(m.group("m")), int(m.group("d")), default_time[0], default_time[1], tzinfo=JST)

    # YYYY/MM/DD
    m = re.search(r"(?P<y>20\d{2})/(?P<m>\d{1,2})/(?P<d>\d{1,2})", t)
    if m:
        return datetime(int(m.group("y")), int(m.group("m")), int(m.group("d")), default_time[0], default_time[1], tzinfo=JST)

    return None

def get(url: str) -> Optional[str]:
    try:
        r = requests.get(url, **REQ_KW)
        if r.ok:
            return r.text
    except Exception:
        return None
    return None

def soupify(html_text: str) -> BeautifulSoup:
    return BeautifulSoup(html_text, "lxml")

def clean_space(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def mk_item(
    _id: str,
    title: str,
    start_at: datetime,
    end_at: Optional[datetime],
    *,
    area: str = "",
    purpose: str = "",
    desc: str = "",
    roads: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    authority: str = "",
    source_url: str = "",
    news_url: Optional[str] = None,
    geometry: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if end_at is None:
        end_at = start_at + timedelta(hours=3)  # デフォ3時間枠
    return {
        "id": _id,
        "title": title,
        "purpose": purpose,
        "desc": desc,
        "authority": authority,
        "area": area,
        "startAt": iso(start_at),
        "endAt": iso(end_at),
        "geometry": geometry or None,
        "roads": roads or [],
        "tags": tags or [],
        "sourceUrl": source_url,
        **({"newsUrl": news_url} if news_url else {}),
    }

# ========= 収集ロジック =========
# 1) 宮内庁（皇族関連） — 行事/ご日程の公表を「日にち+行事名」で拾う
def fetch_kunaicho() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    # 代表的な公表ページ（変更があればURLは適宜直してOK）
    candidates = [
        # 行事・ご予定（例）
        "https://www.kunaicho.go.jp/activity/activity/01/activity01.html",
        # トピックス/ご日程（例）
        "https://www.kunaicho.go.jp/page/koho/show",
    ]
    for url in candidates:
        html_text = get(url)
        if not html_text:
            continue
        s = soupify(html_text)

        # a要素やli/記事カードから「日付＋タイトル」っぽいものを収集
        for a in s.select("a"):
            text = clean_space(a.get_text(" "))
            dt_guess = parse_date_guess(text)
            if not dt_guess:
                continue
            title = text
            title = re.sub(r"^\d{1,2}月\d{1,2}日.?|\d{4}年\d{1,2}月\d{1,2}日.?", "", title).strip(" ・:：-")
            if not title:
                title = "ご日程"
            item = mk_item(
                _id=f"imperial_{dt_guess.date()}_{abs(hash(text))%1_000_000}",
                title=f"皇族行事: {title}",
                start_at=dt_guess.replace(hour=9, minute=0),
                end_at=dt_guess.replace(hour=12, minute=0),
                area="皇居周辺（推定）",
                purpose="公表済みのご日程",
                tags=["imperial"],
                authority="宮内庁",
                source_url=url
            )
            items.append(item)

        # テーブル/リスト形式にも一応対応
        for li in s.select("li, td, p"):
            text = clean_space(li.get_text(" "))
            if len(text) < 6:
                continue
            dt_guess = parse_date_guess(text)
            if not dt_guess:
                continue
            title = re.sub(r"^\d{1,2}月\d{1,2}日.?|\d{4}年\d{1,2}月\d{1,2}日.?", "", text).strip(" ・:：-")
            title = title[:120]
            items.append(
                mk_item(
                    _id=f"imperial_{dt_guess.date()}_{abs(hash(text))%1_000_000}",
                    title=f"皇族行事: {title or '行事'}",
                    start_at=dt_guess.replace(hour=9, minute=0),
                    end_at=dt_guess.replace(hour=12, minute=0),
                    area="皇居周辺（推定）",
                    purpose="公表済みのご日程",
                    tags=["imperial"],
                    authority="宮内庁",
                    source_url=url
                )
            )
    return items

# 2) 首相官邸（首相関連）
def fetch_kantei() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    # 代表URL（予定/会見/日程等）— 実ページに合わせて適宜増強OK
    candidates = [
        "https://www.kantei.go.jp/jp/iken/koukai/",     # 公開情報の入口例
        "https://www.kantei.go.jp/jp/101_kishida/statement/",  # 例：声明/会見など
    ]
    for url in candidates:
        html_text = get(url)
        if not html_text:
            continue
        s = soupify(html_text)
        for a in s.select("a"):
            text = clean_space(a.get_text(" "))
            dt_guess = parse_date_guess(text, default_time=(8, 0))
            if not dt_guess:
                continue
            title = re.sub(r"^\d{1,2}月\d{1,2}日.?|\d{4}年\d{1,2}月\d{1,2}日.?", "", text).strip(" ・:：-")
            if not title:
                title = "首相関連の予定/会見"
            items.append(
                mk_item(
                    _id=f"pm_{dt_guess.date()}_{abs(hash(text))%1_000_000}",
                    title=f"首相関連: {title}",
                    start_at=dt_guess,
                    end_at=dt_guess + timedelta(hours=1),
                    area="官邸〜霞が関（推定）",
                    purpose="公表済みの予定/会見等",
                    tags=["pm"],
                    authority="内閣官房・首相官邸",
                    source_url=url
                )
            )
    return items

# 3) 外務省（国賓関連）
def fetch_mofa() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    candidates = [
        "https://www.mofa.go.jp/mofaj/press/index.html",   # 記者発表一覧（例）
    ]
    for url in candidates:
        html_text = get(url)
        if not html_text:
            continue
        s = soupify(html_text)
        for a in s.select("a"):
            text = clean_space(a.get_text(" "))
            if not any(k in text for k in ["国賓", "公式実務訪問賓客", "歓迎行事", "儀仗", "来日"]):
                # キーワードで粗く絞る
                continue
            dt_guess = parse_date_guess(text, default_time=(10, 0))
            # 日付が無い場合は本文ページに飛んで詳細取得するのが理想だが、まずはタイトルから拾う
            if not dt_guess:
                # 今日〜30日先のどこかに仮置き（タイトルに日付無いパターン）
                dt_guess = jst_now().replace(hour=10, minute=0) + timedelta(days=7)
            title = text[:120]
            items.append(
                mk_item(
                    _id=f"state_{dt_guess.date()}_{abs(hash(text))%1_000_000}",
                    title=f"国賓関連: {title}",
                    start_at=dt_guess,
                    end_at=dt_guess + timedelta(hours=3),
                    area="迎賓館（赤坂離宮）周辺（推定）",
                    purpose="国賓来日に伴う行事/儀仗（公表情報ベース）",
                    tags=["state"],
                    authority="外務省",
                    source_url=url
                )
            )
    return items

# 4) （任意）警視庁/首都高 – “公表された規制告知”のみを拾う
def fetch_traffic() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    candidates = [
        # 例：首都高の交通規制お知らせ/工事情報など（サイト構成に応じて差し替え）
        "https://www.shutoko.jp/roadinfo/event/",   # 仮の例
        # 警視庁の交通規制のお知らせなど
        "https://www.keishicho.metro.tokyo.jp/kotu/kisei/index.html",  # 仮の例
    ]
    for url in candidates:
        html_text = get(url)
        if not html_text:
            continue
        s = soupify(html_text)
        for a in s.select("a"):
            text = clean_space(a.get_text(" "))
            if not any(k in text for k in ["交通規制", "通行止め", "交通規制のお知らせ", "首都高", "羽田", "皇居", "迎賓館", "通行規制"]):
                continue
            dt_guess = parse_date_guess(text, default_time=(7, 0))
            if not dt_guess:
                # 日付不明はスキップ（誤検知を避ける）
                continue
            title = text[:120]
            area = "都内一部（公表範囲）"
            if "皇居" in text:
                area = "皇居周辺"
            elif "迎賓館" in text or "赤坂" in text:
                area = "迎賓館（赤坂）周辺"
            elif "羽田" in text:
                area = "羽田空港周辺/首都高1号羽田線"
            items.append(
                mk_item(
                    _id=f"traffic_{dt_guess.date()}_{abs(hash(text))%1_000_000}",
                    title=f"交通規制: {title}",
                    start_at=dt_guess,
                    end_at=dt_guess + timedelta(hours=4),
                    area=area,
                    purpose="公表済みの交通規制",
                    tags=["imperial","pm","state"],  # どのカテゴリでも参考にしたいので全タグ付与（必要なら調整）
                    authority="公表元",
                    source_url=url
                )
            )
    return items

# ========= 手動追記のマージ =========
def merge_manual(base: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    /data/manual/*.json を読み込み、id一致は上書き。
    """
    out = {i["id"]: i for i in base}
    manu_dir = Path("data/manual")
    if manu_dir.exists():
        for p in manu_dir.glob("*.json"):
            try:
                arr = json.loads(p.read_text(encoding="utf-8"))
                for it in arr:
                    out[it["id"]] = it
            except Exception:
                # 壊れたJSONは無視
                pass
    return list(out.values())

# ========= メイン =========
def main():
    all_items: List[Dict[str, Any]] = []

    # 各ソースを順番に収集（サイトが落ちていても他は続行）
    for fn in (fetch_kunaicho, fetch_kantei, fetch_mofa, fetch_traffic):
        try:
            items = fn()
            all_items.extend(items)
        except Exception as e:
            # 失敗しても止めない
            print(f"[warn] {fn.__name__} failed: {e}", file=sys.stderr)

    # 手動追記をマージ
    all_items = merge_manual(all_items)

    # 未来のイベントを中心に（過去は自然に流れていく）
    now = jst_now()
    kept: List[Dict[str, Any]] = []
    for it in all_items:
        try:
            st = datetime.fromisoformat(it["startAt"])
            # 60日前より古いものは捨てる（履歴を残したいなら調整）
            if st >= now - timedelta(days=60):
                kept.append(it)
        except Exception:
            continue

    # 日付順
    kept.sort(key=lambda x: x.get("startAt", ""))

    # 出力
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(kept, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] wrote {OUT_PATH} with {len(kept)} items")

if __name__ == "__main__":
    main()


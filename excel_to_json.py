# -*- coding: utf-8 -*-
import pandas as pd
import json
from collections import defaultdict, OrderedDict
from pathlib import Path

# ====== 設定 ======
EXCEL_PATH = "卒論_実装用対応表.xlsx"
SHEET_A = "食品ー味覚"
SHEET_B = "味覚ー気分ー音楽"
OUTPUT_JSON = "data.json"

# 味覚の正規化（和⇒英）
TASTE_MAP = {
    "甘味": "sweet", "あまい": "sweet", "sweet": "sweet",
    "酸味": "sour",  "すっぱい": "sour", "sour": "sour",
    "苦味": "bitter","にがい": "bitter","bitter": "bitter",
    "塩味": "salty", "しょっぱい": "salty","salty": "salty",
    "辛味": "spicy", "からい": "spicy","spicy": "spicy",
}

# 気分の正規化（和⇒英：UIのキーに合わせる）
MOOD_MAP = {
    "リラックス": "relaxation", "relax": "relaxation", "relaxation": "relaxation",
    "元気": "excitement", "genki": "excitement", "excitement": "excitement",
    "集中": "focus", "shuchu": "focus", "focus": "focus",
    "落ち着き": "calm", "ochitsuki": "calm", "calm": "calm",
}

# シートBの列名ゆらぎ（候補）
ALIASES_B = {
    "taste":        ["taste", "味覚", "default_taste"],
    "mood":         ["mood", "気分"],
    "artist":       ["artist", "アーティスト", "歌手", "作曲者"],
    "song_title":   ["song_title", "song", "曲名", "title", "楽曲名"],
    "uri":          ["uri", "link", "url", "リンク", "動画", "音源", "path", "file"],
    "rank":         ["rank", "順位", "優先度"],
    "weight":       ["weight", "重み", "抽選重み"],
    "instrumental": ["instrumental", "インスト", "歌詞なし", "instrument", "inst"]
}

def find_col(df: pd.DataFrame, keys, required=True):
    cols = [c for c in df.columns]
    for k in keys:
        if k in cols:
            return k
    if required:
        raise KeyError(f"必須列が見つかりません: 候補={keys}")
    return None

def norm_taste(x: str) -> str:
    if pd.isna(x): return ""
    s = str(x).strip()
    return TASTE_MAP.get(s, s.lower())

def norm_mood(x: str) -> str:
    if pd.isna(x): return ""
    s = str(x).strip()
    return MOOD_MAP.get(s, s.lower())

def to_bool_or_none(x):
    if pd.isna(x): return None
    if isinstance(x, bool): return x
    s = str(x).strip().lower()
    if s in ("true", "1", "t", "yes", "y", "はい", "有", "インスト", "instrumental"): return True
    if s in ("false", "0", "f", "no", "n", "いいえ", "無", "歌詞あり", "vocal"): return False
    return None

def main():
    # === Excel読み込み ===
    try:
        sheetA = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_A)
        sheetB = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_B)
    except Exception as e:
        print("❌ Excelファイルまたはシート名が見つかりません。")
        print("エラー内容:", e)
        return

    # 列名正規化
    sheetA.columns = sheetA.columns.str.strip()
    sheetB.columns = sheetB.columns.str.strip()

    # ---- シートA：食品ー味覚（既存スキーマ）
    # 期待：food_id / food_name / default_taste / allow_choice / option_taste
    # 小文字比較用に辞書化
    a_cols = {c.lower(): c for c in sheetA.columns}
    reqA = ["food_id", "food_name", "default_taste", "allow_choice", "option_taste"]
    for col in reqA:
        if col not in a_cols:
            print(f"⚠️ シートAに '{col}' 列が見つかりません（大小/全角半角/空白を確認）")

    # 出力用ベース（食品ごと）
    data = OrderedDict()
    for _, r in sheetA.iterrows():
        food_id        = str(r.get(a_cols.get("food_id", ""), "")).strip()
        food_name      = str(r.get(a_cols.get("food_name", ""), "")).strip()
        default_taste  = norm_taste(r.get(a_cols.get("default_taste", ""), ""))
        allow_choice   = bool(r.get(a_cols.get("allow_choice", False)))
        option_taste   = r.get(a_cols.get("option_taste", None))

        if not food_name:
            continue

        entry = data.get(food_name)
        if entry is None:
            entry = {
                "id": food_id,
                "taste": default_taste,
                "options": [],
                "music": {  # 後で taste&moood で埋める
                    "relaxation": [],
                    "excitement": [],
                    "focus": [],
                    "calm": []
                }
            }
            data[food_name] = entry

        # option_taste は複数行で現れる可能性があるため追記方式
        if pd.notna(option_taste) and str(option_taste).strip():
            entry["options"].append(norm_taste(option_taste))

    # ---- シートB：味覚ー気分ー音楽（縦持ち1行=1曲）
    b = sheetB.copy()
    b.columns = [c.strip() for c in b.columns]

    # 列解決
    c_taste = find_col(b, ALIASES_B["taste"], required=True)
    c_mood  = find_col(b, ALIASES_B["mood"], required=True)
    c_title = find_col(b, ALIASES_B["song_title"], required=True)
    c_uri   = find_col(b, ALIASES_B["uri"], required=True)
    c_artist= find_col(b, ALIASES_B["artist"], required=False)
    c_rank  = find_col(b, ALIASES_B["rank"], required=False)
    c_w     = find_col(b, ALIASES_B["weight"], required=False)
    c_inst  = find_col(b, ALIASES_B["instrumental"], required=False)

    # 正規化と必須欠損除外（NaN対策）
    b["__taste"] = b[c_taste].map(norm_taste)
    b["__mood"]  = b[c_mood].map(norm_mood)
    b["__title"] = b[c_title].astype(str).str.strip()
    b["__uri"]   = b[c_uri].astype(str).str.strip()

    b = b.dropna(subset=["__taste", "__mood", "__title", "__uri"])
    b = b[(b["__taste"] != "") & (b["__mood"] != "") & (b["__title"] != "") & (b["__uri"] != "")].copy()

    # 型整備
    if c_rank:
        b["__rank"] = pd.to_numeric(b[c_rank], errors="coerce")
    else:
        b["__rank"] = pd.NA

    if c_w:
        b["__weight"] = pd.to_numeric(b[c_w], errors="coerce").fillna(1.0)
    else:
        b["__weight"] = 1.0

    if c_inst:
        b["__inst"] = b[c_inst].map(to_bool_or_none)
    else:
        b["__inst"] = None

    if c_artist:
        b["__artist"] = b[c_artist].astype(str).str.strip()
    else:
        b["__artist"] = None

    # rank がある場合は味覚×気分×rankで安定ソート、なければ味覚×気分の行順維持
    sort_keys = ["__taste", "__mood"]
    if b["__rank"].notna().any():
        sort_keys.append("__rank")
    b = b.sort_values(sort_keys, kind="stable")

    # 味覚×気分ごとの曲リスト辞書を作成
    taste_mood_tracks = defaultdict(lambda: defaultdict(list))
    for _, r in b.iterrows():
        track = {
            "title": r["__title"],
            "uri": r["__uri"]
        }
        if r["__artist"] and str(r["__artist"]).lower() != "nan":
            track["artist"] = r["__artist"]
        if pd.notna(r["__rank"]):
            try:
                track["rank"] = int(r["__rank"])
            except Exception:
                pass
        if r["__weight"] is not None:
            track["weight"] = float(r["__weight"])
        if r["__inst"] is not None:
            track["instrumental"] = bool(r["__inst"])

        taste_mood_tracks[r["__taste"]][r["__mood"]].append(track)

    # 食品ごとに default_taste の曲を割り当て（気分別リスト）
    for food_name, info in data.items():
        base_taste = info.get("taste", "")
        # まずdefault_taste
        if base_taste in taste_mood_tracks:
            for mood_key, tracks in taste_mood_tracks[base_taste].items():
                data[food_name]["music"][mood_key] = tracks

        # option_tasteがある場合、必要なら追加ロジックをここに（例：tasteセレクタで切替）
        # 今はUIでtasteを切り替えて再取得する前提のため、JSONはdefaultを格納。

    # JSON出力
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ JSONファイルを出力しました: {Path(OUTPUT_JSON).resolve()}")
    print("   ・食品は default_taste に基づき、各気分ごとの曲リストを付与しました。")
    print("   ・シートBで必須列欠損の行は除外済み（NaNが出力に混ざらない設計）。")

if __name__ == "__main__":
    main()


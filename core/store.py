"""数据层：读刷B站插件 / 日记插件的数据，读写打分。"""

from __future__ import annotations

import base64
import json
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any

try:  # AstrBot 运行时提供
    from astrbot.api import logger
except Exception:  # 便于脱离 AstrBot 单测
    import logging

    logger = logging.getLogger("dafeiyu_panel")


def _read_json(path: Path, default: Any) -> Any:
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except Exception as e:
        logger.warning(f"[dafeiyu-panel] 读 {path} 失败：{e}")
        return default


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _data_root() -> Path:
    try:
        from astrbot.core.utils.astrbot_path import get_astrbot_data_path

        return Path(get_astrbot_data_path())
    except Exception:
        return Path(os.getcwd()) / "data"


def _plugin_data_root(plugin_name: str) -> Path:
    try:
        from astrbot.core.utils.astrbot_path import get_astrbot_plugin_data_path

        return Path(get_astrbot_plugin_data_path()) / plugin_name
    except Exception:
        return _data_root() / "plugin_data" / plugin_name


def _as_ts(value: Any) -> float:
    """把各种时间戳写法统一成 epoch 秒。

    日记/教学库里的 ts 可能是 float/int，也可能被写成 ISO 字符串
    （"2026-10-31T22:30:03" 这种），这里全部兜住，读不出来就当 0。
    """
    if isinstance(value, (int, float)):
        return float(value)
    txt = str(value or "").strip()
    if not txt:
        return 0.0
    try:
        return float(txt)
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(txt.replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


class PanelData:
    """一个实例负责管理路径、缓存与打分读写。"""

    def __init__(self, conf: dict | None = None, plugin_name: str = "astrbot_plugin_dafeiyu_panel"):
        self.conf = conf or {}
        self.plugin_name = plugin_name
        self.root = _data_root()
        own = str(self.conf.get("own_dir") or "").strip()
        self.own_dir = Path(own) if own else _plugin_data_root(plugin_name)
        self.own_dir.mkdir(parents=True, exist_ok=True)
        self.ratings_file = self.own_dir / "ratings.json"

        self.state_file = Path(
            str(self.conf.get("bili_state_file") or "").strip()
            or self.root / "bili_whale" / "state.json"
        )
        self.cover_dir = Path(
            str(self.conf.get("cover_dir") or "").strip()
            or self.state_file.parent / "covers"
        )
        self.journal_file = Path(
            str(self.conf.get("journal_file") or "").strip()
            or self.root / "whale_journal" / "entries.jsonl"
        )

        self._state_cache: tuple[float, dict] | None = None
        self._ratings_cache: tuple[float, dict] | None = None

    # ------------------------------------------------------------ 基础读取
    def state(self) -> dict:
        try:
            mtime = self.state_file.stat().st_mtime
        except OSError:
            return {}
        if self._state_cache and self._state_cache[0] == mtime:
            return self._state_cache[1]
        data = _read_json(self.state_file, {})
        if not isinstance(data, dict):
            data = {}
        self._state_cache = (mtime, data)
        return data

    def ratings(self) -> dict:
        try:
            mtime = self.ratings_file.stat().st_mtime
        except OSError:
            return {}
        if self._ratings_cache and self._ratings_cache[0] == mtime:
            return self._ratings_cache[1]
        data = _read_json(self.ratings_file, {})
        if not isinstance(data, dict):
            data = {}
        data.pop("version", None)
        self._ratings_cache = (mtime, data)
        return data

    # ------------------------------------------------------------ 观看列表
    def _day_of(self, ts: int) -> tuple[str, str]:
        try:
            dt = datetime.fromtimestamp(int(ts))
        except Exception:
            return "", ""
        return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")

    def items(self) -> list[dict]:
        """把 state.seen + feedback + 本地 ratings 合成一个列表（新的在前）。"""
        st = self.state()
        seen = st.get("seen") or {}
        feedback = st.get("feedback") or {}
        mine = self.ratings()
        has_covers = self.cover_dir.is_dir()

        rows: list[dict] = []
        for bvid, info in seen.items():
            if not isinstance(info, dict):
                continue
            ts = int(info.get("ts") or 0)
            day, hm = self._day_of(ts)
            fb = dict(feedback.get(bvid) or {})
            fb.update(mine.get(bvid) or {})
            stars = int(fb.get("stars") or 0)
            rows.append(
                {
                    "bvid": bvid,
                    "title": str(info.get("title") or bvid),
                    "day": day,
                    "hm": hm,
                    "ts": ts,
                    "score": int(info.get("score") or 0),
                    "shared": bool(info.get("shared")),
                    "keyword": str(info.get("keyword") or ""),
                    "note": str(fb.get("note") or ""),
                    "stars": stars,
                    "fav": bool(fb.get("fav")) or stars >= 5,
                    "cover": bool(has_covers and (self.cover_dir / f"{bvid}.jpg").exists()),
                }
            )
        rows.sort(key=lambda r: r["ts"], reverse=True)
        return rows

    def summary(self, rows: list[dict] | None = None) -> dict:
        rows = rows if rows is not None else self.items()
        rated = [r for r in rows if r["stars"] > 0]
        favs = [r for r in rows if r["fav"]]
        shared = [r for r in rows if r["shared"]]
        return {
            "total": len(rows),
            "rated": len(rated),
            "todo": len(rows) - len(rated),
            "fav": len(favs),
            "shared": len(shared),
            "avg": round(sum(r["stars"] for r in rated) / len(rated), 1) if rated else 0.0,
            "days": len({r["day"] for r in rows if r["day"]}),
        }

    def page(self, *, filter_: str = "all", q: str = "", page: int = 1, size: int = 24) -> dict:
        rows = self.items()
        q = (q or "").strip().lower()
        if q:
            rows = [
                r
                for r in rows
                if q in r["title"].lower()
                or q in r["note"].lower()
                or q in r["keyword"].lower()
                or q in r["bvid"].lower()
            ]
        if filter_ == "shared":
            rows = [r for r in rows if r["shared"]]
        elif filter_ == "unshared":
            rows = [r for r in rows if not r["shared"]]
        elif filter_ == "fav":
            rows = [r for r in rows if r["fav"]]
        elif filter_ == "todo":
            rows = [r for r in rows if r["stars"] <= 0]
        elif filter_ == "done":
            rows = [r for r in rows if r["stars"] > 0]

        size = max(1, min(int(size or 24), 100))
        page = max(1, int(page or 1))
        total = len(rows)
        start = (page - 1) * size
        return {
            "total": total,
            "page": page,
            "size": size,
            "pages": max(1, (total + size - 1) // size),
            "summary": self.summary(),
            "items": rows[start : start + size],
        }

    # ------------------------------------------------------------ 封面
    def cover_b64(self, bvid: str) -> str | None:
        if not bvid.startswith("BV"):
            return None
        f = self.cover_dir / f"{bvid}.jpg"
        if not f.is_file():
            return None
        try:
            data = f.read_bytes()
        except OSError:
            return None
        if len(data) > 1_500_000:  # 太大就算了，不让接口变慢
            return None
        return base64.b64encode(data).decode()

    # ------------------------------------------------------------ 打分
    def rate(self, bvid: str, stars: int, note: str = "", fav: Any = None) -> dict:
        rows = {r["bvid"]: r for r in self.items()}
        cur = rows.get(bvid)
        if cur is None:
            return {"ok": False, "message": "这个视频不在记录里"}
        stars = max(0, min(int(stars or 0), 5))
        if fav is None:
            fav = cur["fav"] if stars else False
        fav = bool(fav) or stars >= 5

        store = _read_json(self.ratings_file, {})
        if not isinstance(store, dict):
            store = {}
        store.pop("version", None)
        if stars <= 0 and not str(note).strip() and not fav:
            store.pop(bvid, None)
        else:
            store[bvid] = {
                "stars": stars,
                "note": str(note)[:500],
                "fav": fav,
                "ts": int(time.time()),
            }
        store["version"] = 1
        _write_json(self.ratings_file, store)
        self._state_cache = None
        self._ratings_cache = None

        synced = False
        if self.conf.get("sync_to_bili_state", True):
            synced = self._sync_to_state(bvid, stars, str(note)[:500], fav)
        return {"ok": True, "stars": stars, "fav": fav, "synced": synced}

    def _sync_to_state(self, bvid: str, stars: int, note: str, fav: bool) -> bool:
        """把打分写进 bili_whale 的 state.json（她下一轮选题会读 feedback）。"""
        path = self.state_file
        if not path.is_file():
            return False
        data = _read_json(path, None)
        if not isinstance(data, dict):
            return False
        fb = data.get("feedback")
        if not isinstance(fb, dict):
            fb = {}
        if stars <= 0 and not note and not fav:
            fb.pop(bvid, None)
        else:
            fb[bvid] = {"stars": stars, "note": note, "fav": fav, "ts": int(time.time())}
        data["feedback"] = fb
        try:
            bak = path.with_suffix(path.suffix + ".bak-panel")
            if path.is_file():
                shutil.copy2(path, bak)
            _write_json(path, data)
            self._state_cache = None
            return True
        except Exception as e:
            logger.warning(f"[dafeiyu-panel] 写 state.json 失败：{e}")
            return False

    # ------------------------------------------------------------ 日记
    def journal(self, *, limit: int = 300, q: str = "") -> list[dict]:
        out: list[dict] = []
        if not self.journal_file.is_file():
            return out
        q = (q or "").strip().lower()
        try:
            with open(self.journal_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                    except Exception:
                        continue
                    if not isinstance(d, dict):
                        continue
                    body = str(d.get("body") or "")
                    title = str(d.get("title") or "")
                    mood = str(d.get("mood") or "")
                    videos = [str(v) for v in (d.get("videos") or []) if v]
                    lessons = [str(v) for v in (d.get("lessons") or []) if v]
                    if q and not (
                        q in body.lower()
                        or q in title.lower()
                        or q in mood.lower()
                        or any(q in v.lower() for v in videos + lessons)
                    ):
                        continue
                    span = d.get("span") or []
                    out.append(
                        {
                            "ts": int(_as_ts(d.get("ts"))),
                            "day": str(d.get("day") or ""),
                            "hm": str(d.get("hm") or ""),
                            "mood": mood,
                            "title": title,
                            "body": body,
                            "videos": videos,
                            "lessons": lessons,
                            "chat_count": int(d.get("chat_count") or 0),
                            "span": [str(x) for x in span][:2],
                        }
                    )
        except OSError:
            return []
        out.sort(key=lambda x: x["ts"], reverse=True)
        return out[: max(1, int(limit or 300))]

    # ------------------------------------------------------------ 主人画像
    def profile(self) -> dict:
        """读日记插件算出来的主人画像（owner_profile.json）。"""
        path = self.journal_file.parent / "owner_profile.json"
        data = _read_json(path, {})
        if not isinstance(data, dict):
            data = {}
        mood = data.get("mood") if isinstance(data.get("mood"), dict) else {}
        sleep = data.get("sleep") if isinstance(data.get("sleep"), dict) else {}

        def _list(key: str) -> list[str]:
            v = data.get(key) or []
            if isinstance(v, str):
                v = [x for x in v.replace("，", ",").split(",") if x.strip()]
            return [str(x).strip() for x in v if str(x).strip()][:16]

        try:
            idx = int(mood.get("index") or 0)
        except Exception:
            idx = 0
        return {
            "has_data": bool(data),
            "updated_at": str(data.get("updated_at") or ""),
            "days_covered": int(data.get("days_covered") or 0),
            "personality": _list("personality"),
            "habits": _list("habits"),
            "catchphrases": _list("catchphrases"),
            "highlights": _list("highlights"),
            "summary": str(data.get("summary") or ""),
            "period": data.get("period") if isinstance(data.get("period"), dict) else {},
            "timeline": [t for t in (data.get("timeline") or []) if isinstance(t, dict)][-365:],
            "mood": {
                "index": max(0, min(10, idx)),
                "label": str(mood.get("label") or "—"),
                "note": str(mood.get("note") or ""),
            },
            "sleep": {
                "quality": str(sleep.get("quality") or "—"),
                "note": str(sleep.get("note") or ""),
            },
            "file": str(path),
        }

    # ------------------------------------------------------------ 教我的
    def _lessons_file(self) -> Path:
        return self.journal_file.parent / "lessons.json"

    def _lessons_data(self) -> dict:
        data = _read_json(self._lessons_file(), {})
        if not isinstance(data, dict):
            data = {}
        if not isinstance(data.get("items"), list):
            data["items"] = []
        if not isinstance(data.get("trash"), list):
            data["trash"] = []
        return data

    @staticmethod
    def _cats(data: dict) -> list[str]:
        out = ["黑话", "梗", "调情", "其他"]
        for c in data.get("custom_categories") or []:
            c = str(c or "").strip()
            if c and c not in out:
                out.append(c)
        return out

    @staticmethod
    def _coerce_cat(value, cats: list[str]) -> str:
        txt = str(value or "").strip()
        if not txt:
            return "其他"
        if txt in cats:
            return txt
        for c in ("黑话", "梗", "调情", "其他"):
            if c in txt:
                return c
        if 1 <= len(txt) <= 12 and not txt.isdigit():
            return txt
        return "其他"

    def lessons(self, *, q: str = "", limit: int = 400) -> dict:
        """读日记插件的教学库（lessons.json）：动态分类 + 完整对话 + 回收站。"""
        path = self._lessons_file()
        data = self._lessons_data()
        items = [it for it in data.get("items") or [] if isinstance(it, dict)]
        cats = self._cats(data)
        q = (q or "").strip().lower()
        groups: dict[str, list[dict]] = {c: [] for c in cats}
        total = 0
        for it in items:
            text = str(it.get("text") or "").strip()
            if not text:
                continue
            cat = self._coerce_cat(it.get("category"), cats)
            if q and q not in text.lower() and q not in cat and q not in str(it.get("context") or "").lower():
                continue
            groups.setdefault(cat, []).append(
                {
                    "id": str(it.get("id") or ""),
                    "text": text[:200],
                    "category": cat,
                    "note": str(it.get("note") or ""),
                    "context": str(it.get("context") or ""),
                    "title": str(it.get("title") or ""),
                    "gist": str(it.get("gist") or ""),
                    "source": str(it.get("source") or ""),
                    "day": str(it.get("day") or ""),
                    "hits": int(it.get("hits") or 1),
                    "ts": _as_ts(it.get("ts")),
                }
            )
            total += 1
        for c in list(groups):
            groups[c].sort(key=lambda x: x["ts"], reverse=True)
            groups[c] = groups[c][: max(1, int(limit or 400))]
        trash = []
        now = time.time()
        for it in data.get("trash") or []:
            if not isinstance(it, dict):
                continue
            try:
                ts = float(it.get("deleted_at") or 0)
            except (TypeError, ValueError):
                ts = 0.0
            trash.append(
                {
                    "id": str(it.get("id") or ""),
                    "text": str(it.get("text") or "")[:200],
                    "category": self._coerce_cat(it.get("category"), cats),
                    "context": str(it.get("context") or ""),
                    "deleted_ts": str(it.get("deleted_ts") or ""),
                    "days_left": max(0, int(30 - (now - ts) / 86400)) if ts else 30,
                }
            )
        return {
            "total": total,
            "counts": {c: len(groups.get(c, [])) for c in cats},
            "categories": cats,
            "groups": [{"category": c, "items": groups.get(c, [])} for c in cats],
            "trash": trash,
            "updated_at": str(data.get("updated_at") or ""),
            "file": str(path),
        }

    # -------------------------------------------------- 教学库写操作
    def add_lesson_category(self, name: str) -> dict:
        name = " ".join(str(name or "").split())[:12]
        if not name:
            return {"ok": False, "message": "分类名不能空"}
        data = self._lessons_data()
        cats = self._cats(data)
        if name in cats:
            return {"ok": False, "message": "这个分类已经有了", "categories": cats}
        extra = [str(c) for c in (data.get("custom_categories") or []) if str(c).strip()]
        extra.append(name)
        data["custom_categories"] = extra
        data["version"] = data.get("version") or 1
        _write_json(self._lessons_file(), data)
        return {"ok": True, "message": f"加好了「{name}」", "categories": self._cats(data)}

    def set_lesson_category(self, lid: str, category: str) -> dict:
        lid = str(lid or "").strip()
        data = self._lessons_data()
        cats = self._cats(data)
        cat = self._coerce_cat(category, cats)
        for it in data.get("items") or []:
            if str(it.get("id")) == lid:
                it["category"] = cat
                _write_json(self._lessons_file(), data)
                return {"ok": True, "message": f"归到「{cat}」了", "category": cat}
        return {"ok": False, "message": "没找到这条"}

    def delete_lesson(self, lid: str) -> dict:
        lid = str(lid or "").strip()
        data = self._lessons_data()
        items = data.get("items") or []
        for i, it in enumerate(items):
            if str(it.get("id")) == lid:
                gone = items.pop(i)
                gone["deleted_ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
                gone["deleted_at"] = time.time()
                trash = data.get("trash") or []
                trash.insert(0, gone)
                data["items"] = items
                data["trash"] = trash[:400]
                _write_json(self._lessons_file(), data)
                return {"ok": True, "message": "已移入回收站（30 天内可还原）"}
        return {"ok": False, "message": "没找到这条"}

    def restore_lesson(self, lid: str) -> dict:
        lid = str(lid or "").strip()
        data = self._lessons_data()
        trash = data.get("trash") or []
        for i, it in enumerate(trash):
            if str(it.get("id")) == lid:
                back = trash.pop(i)
                back.pop("deleted_ts", None)
                back.pop("deleted_at", None)
                items = data.get("items") or []
                items.append(back)
                data["items"] = items
                data["trash"] = trash
                _write_json(self._lessons_file(), data)
                return {"ok": True, "message": "还原好了"}
        return {"ok": False, "message": "回收站里没有这条"}

    # ------------------------------------------------------------ 状态
    def status(self) -> dict:
        return {
            "state_file": str(self.state_file),
            "state_exists": self.state_file.is_file(),
            "cover_dir": str(self.cover_dir),
            "cover_exists": self.cover_dir.is_dir(),
            "journal_file": str(self.journal_file),
            "journal_exists": self.journal_file.is_file(),
            "ratings_file": str(self.ratings_file),
            "profile_file": str(self.journal_file.parent / "owner_profile.json"),
            "profile_exists": (self.journal_file.parent / "owner_profile.json").is_file(),
            "lessons_file": str(self.journal_file.parent / "lessons.json"),
            "lessons_exists": (self.journal_file.parent / "lessons.json").is_file(),
        }

"""核心数据层单测：不依赖 AstrBot，直接跑 python tests/test_store.py。"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.store import PanelData  # noqa: E402

OK = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  PASS {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name} {detail}")


def build_tmp() -> tuple[Path, Path, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="panel-test-"))
    covers = tmp / "covers"
    covers.mkdir()
    (covers / "BV1aaaaaaaaa.jpg").write_bytes(b"\xff\xd8\xff\xd9")
    state = {
        "seen": {
            "BV1aaaaaaaaa": {"ts": 1793300000, "title": "视频甲", "score": 16, "shared": True},
            "BV1bbbbbbbbb": {"ts": 1793200000, "title": "视频乙", "score": 9, "shared": False},
            "BV1ccccccccc": {"ts": 1793100000, "title": "视频丙", "score": 18, "shared": True},
        },
        "feedback": {"BV1ccccccccc": {"stars": 5, "note": "这种多推", "fav": True, "ts": 1793200000}},
        "shares": {},
    }
    sp = tmp / "state.json"
    sp.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    entries = [
        {"ts": 1793300000, "day": "2026-10-30", "hm": "22:30", "mood": "有点得意", "title": "测试",
         "body": "今天被教了一件事", "videos": ["视频甲"], "chat_count": 12, "span": ["20:00", "22:30"],
         "lessons": ["你要记住我"]},
    ]
    jp = tmp / "entries.jsonl"
    jp.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in entries) + "\n", encoding="utf-8")
    return tmp, sp, jp


def main() -> None:
    tmp, sp, jp = build_tmp()
    conf = {"bili_state_file": str(sp), "cover_dir": str(tmp / "covers"), "journal_file": str(jp),
            "sync_to_bili_state": True, "own_dir": str(tmp / "own")}
    d = PanelData(conf, "astrbot_plugin_dafeiyu_panel")

    page = d.page(filter_="all", q="", page=1, size=24)
    check("列表条数", page["total"] == 3, str(page["total"]))
    check("按时间倒序", page["items"][0]["bvid"] == "BV1aaaaaaaaa", page["items"][0]["bvid"])
    check("汇总-已打分", page["summary"]["rated"] == 1, str(page["summary"]))
    check("汇总-收藏", page["summary"]["fav"] == 1, str(page["summary"]))
    check("汇总-推给我的", page["summary"]["shared"] == 2, str(page["summary"]))
    check("封面标记", page["items"][0]["cover"] is True)
    check("封面内容可读", bool(d.cover_b64("BV1aaaaaaaaa")))
    check("无封面返回 None", d.cover_b64("BV1bbbbbbbbb") is None)

    check("筛选-收藏", len(d.page(filter_="fav")["items"]) == 1)
    check("筛选-待我评价", len(d.page(filter_="todo")["items"]) == 2)
    check("筛选-评过的", len(d.page(filter_="done")["items"]) == 1)
    check("筛选-推给我的", len(d.page(filter_="shared")["items"]) == 2)
    check("搜索", len(d.page(filter_="all", q="视频乙")["items"]) == 1)

    r = d.rate("BV1bbbbbbbbb", 4, "还行", False)
    check("打分成功", r.get("ok") is True, str(r))
    check("打分落盘", d.ratings()["BV1bbbbbbbbb"]["stars"] == 4)
    check("同步到 state", json.loads(sp.read_text(encoding="utf-8"))["feedback"]["BV1bbbbbbbbb"]["stars"] == 4)
    check("同步前有备份", (tmp / "state.json.bak-panel").exists())

    d.rate("BV1bbbbbbbbb", 5, "", True)
    check("五星自动收藏", d.ratings()["BV1bbbbbbbbb"]["fav"] is True)
    check("收藏进筛选", len(d.page(filter_="fav")["items"]) == 2)

    check("打分夹紧-高分", d.rate("BV1aaaaaaaaa", 9, "", False)["stars"] == 5)
    low = d.rate("BV1aaaaaaaaa", -3, "", False)
    check("打分夹紧-低分清掉评级", low["stars"] == 0 and "BV1aaaaaaaaa" not in d.ratings())
    check("非法 bvid 拒绝", d.rate("nonsense", 3, "", False).get("ok") is False)

    j = d.journal(limit=10, q="")
    check("日记条数", len(j) == 1, str(len(j)))
    check("日记字段", j[0]["mood"] == "有点得意" and j[0]["lessons"] == ["你要记住我"])
    check("日记搜索命中", len(d.journal(limit=10, q="教了")) == 1)
    check("日记搜索不命中", len(d.journal(limit=10, q="不存在的内容")) == 0)

    st = d.status()
    check("状态里有 state 路径", st["state_file"].endswith("state.json") and st["state_exists"] is True)
    check("状态里标注日记文件", st["journal_exists"] is True)

    # 数据文件不存在时不应崩
    d2 = PanelData({"bili_state_file": str(tmp / "nope.json"), "cover_dir": str(tmp / "nocovers"),
                    "journal_file": str(tmp / "nope.jsonl"), "own_dir": str(tmp / "own2")}, "x")
    check("缺文件时列表为空", d2.page(filter_="all")["total"] == 0)
    check("缺文件时日记为空", len(d2.journal(limit=5, q="")) == 0)

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n结果：{OK} 通过 / {FAIL} 失败")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()

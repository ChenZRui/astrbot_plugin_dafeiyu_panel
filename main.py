"""大肥鱼面板：把「她刷过的视频」和「她的日记本」搬进 AstrBot 面板。"""

from __future__ import annotations

import re
from typing import Any

from astrbot.api import logger
from astrbot.api.event import filter
from astrbot.api.star import Context, Star
from astrbot.api.web import error_response, json_response, request

from .core.store import PanelData

PLUGIN_NAME = "astrbot_plugin_dafeiyu_panel"
_BVID_RE = re.compile(r"^BV[0-9A-Za-z]{8,14}$")


class DafeiyuPanel(Star):
    def __init__(self, context: Context, config: dict | None = None):
        super().__init__(context)
        self.conf = config or {}
        self.data = PanelData(self.conf, PLUGIN_NAME)

        routes = [
            (f"/{PLUGIN_NAME}/items", self.api_items, ["GET"], "视频列表（分页/筛选/搜索）"),
            (f"/{PLUGIN_NAME}/cover", self.api_cover, ["GET"], "单张封面（base64）"),
            (f"/{PLUGIN_NAME}/rate", self.api_rate, ["POST"], "打分/写评价/收藏"),
            (f"/{PLUGIN_NAME}/journal", self.api_journal, ["GET"], "日记列表"),
            (f"/{PLUGIN_NAME}/status", self.api_status, ["GET"], "数据源状态"),
        ]
        for route, handler, methods, desc in routes:
            try:
                context.register_web_api(route, handler, methods, desc)
            except Exception as e:  # 老版本 AstrBot 没有这个 API
                logger.warning(f"[dafeiyu-panel] 注册 Web API 失败（{route}）：{e}")

        st = self.data.status()
        logger.info(
            "[dafeiyu-panel] 已加载｜state=%s（%s）｜covers=%s｜journal=%s"
            % (
                st["state_file"],
                "有" if st["state_exists"] else "无",
                "有" if st["cover_exists"] else "无",
                "有" if st["journal_exists"] else "无",
            )
        )

    # ---------------------------------------------------------------- 工具
    def _enabled(self) -> bool:
        return bool(self.conf.get("enable", True))

    def _size(self) -> int:
        try:
            return max(1, min(int(self.conf.get("page_size", 24) or 24), 100))
        except Exception:
            return 24

    # ---------------------------------------------------------------- API
    async def api_items(self):
        """GET items?filter=all&q=&page=1&size="""
        if not self._enabled():
            return error_response("面板未启用", status_code=403)
        filter_ = request.query.get("filter") or "all"
        q = request.query.get("q") or ""
        page = request.query.get("page", 1, type=int) or 1
        size = request.query.get("size", 0, type=int) or self._size()
        payload = self.data.page(filter_=filter_, q=q, page=page, size=size)
        show_score = bool(self.conf.get("show_score", True))
        for item in payload["items"]:
            if not show_score:
                item["score"] = 0
                item["keyword"] = ""
        payload["allow_edit"] = bool(self.conf.get("allow_edit", True))
        payload["status"] = self.data.status()
        return json_response(payload)

    async def api_cover(self):
        """GET cover?bvid=BVxxxx"""
        bvid = (request.query.get("bvid") or "").strip()
        if not _BVID_RE.match(bvid):
            return error_response("bvid 不合法", status_code=400)
        b64 = self.data.cover_b64(bvid)
        if not b64:
            return json_response({"bvid": bvid, "data": None})
        return json_response({"bvid": bvid, "data": b64})

    async def api_rate(self):
        """POST rate {bvid, stars, note, fav}"""
        if not self._enabled():
            return error_response("面板未启用", status_code=403)
        if not bool(self.conf.get("allow_edit", True)):
            return error_response("面板是只读的（allow_edit=false）", status_code=403)
        body = await request.json(default={})
        if not isinstance(body, dict):
            return error_response("请求体不是 JSON 对象", status_code=400)
        bvid = str(body.get("bvid") or "").strip()
        if not _BVID_RE.match(bvid):
            return error_response("bvid 不合法", status_code=400)
        try:
            stars = int(body.get("stars") or 0)
        except Exception:
            stars = 0
        result = self.data.rate(
            bvid,
            stars,
            str(body.get("note") or ""),
            body.get("fav"),
        )
        if not result.get("ok"):
            return error_response(str(result.get("message") or "保存失败"), status_code=400)
        return json_response(result)

    async def api_journal(self):
        """GET journal?q=&limit="""
        if not self._enabled():
            return error_response("面板未启用", status_code=403)
        q = request.query.get("q") or ""
        try:
            limit = int(request.query.get("limit", 0, type=int) or 0)
        except Exception:
            limit = 0
        limit = limit or int(self.conf.get("journal_limit", 300) or 300)
        entries = self.data.journal(limit=limit, q=q)
        days: dict[str, int] = {}
        for e in entries:
            days[e["day"]] = days.get(e["day"], 0) + 1
        return json_response(
            {
                "total": len(entries),
                "days": [{"day": d, "n": n} for d, n in sorted(days.items(), reverse=True)],
                "entries": entries,
                "status": self.data.status(),
            }
        )

    async def api_status(self):
        return json_response(
            {
                "enabled": self._enabled(),
                "allow_edit": bool(self.conf.get("allow_edit", True)),
                "summary": self.data.summary(),
                "sources": self.data.status(),
            }
        )

    # ---------------------------------------------------------------- 指令
    @filter.command("大肥鱼面板")
    async def cmd_panel(self, event):
        """看看面板在哪打开。"""
        yield event.plain_result(
            "面板地址：AstrBot 网页 → 插件 → 大肥鱼面板 → 打开视图\n"
            "里面有两个：『她看过什么』打分台、『她的日记本』。\n"
            "手机也是同一个地址，用手机浏览器打开面板就行。"
        )

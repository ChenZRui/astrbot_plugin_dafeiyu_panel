# 大肥鱼面板（B站打分台 + 日记本）

> 把「她刷了什么视频」和「她写了什么日记」搬进 AstrBot 面板。点星星打分、写两句评价、一键收藏，`data/bili_whale/state.json` 的 `state.json` 里就会多一条反馈，下一轮选题按你的口味调权重。

一套面板，两个视图，手机和电脑都能开：

| 视图 | 内容 |
| --- | --- |
| **她看过什么**（打分台） | 按天分组、带封面的视频卡；★ 打分、写评价、点收藏；筛选「她推给我的 / 没推给我的 / 收藏 / 待我评价 / 评过的」 |
| **她的日记本** | 她自己写的日记：心情标签、正文、看过的视频、「主人教我的」条目，左侧按天翻页 |

![打分台](docs/watch.png)
![日记本](docs/journal.png)

---

## 它是什么 / 不是什么

**是**：一个只读 + 打分的面板插件。它读另外两个插件的数据文件，把内容渲染成 AstrBot 面板里的两个页面。

**不是**：它自己不会刷 B 站、不会写日记。数据来源：

| 数据 | 来源插件 | 文件 |
| --- | --- | --- |
| 看过的视频、分数、是否推给你 | `astrbot_plugin_bili_whale`（刷 B 站的大肥鱼） | `data/bili_whale/state.json` + `data/bili_whale/covers/*.jpg` |
| 日记正文、心情、看了什么 | `astrbot_plugin_whale_journal`（大肥鱼日记本） | `data/whale_journal/entries.jsonl` |

两个都没装也能装这个插件，页面会提示「还没有数据」；装上之后自动出现内容。

---

## 安装

### 方式一：AstrBot 插件市场（推荐）

面板 → 插件 → 插件市场 → 搜「大肥鱼面板」→ 安装 → 重载插件。

### 方式二：手动放进插件目录

```bash
cd /opt/astrbot/data/plugins
git clone https://github.com/ChenZRui/astrbot_plugin_dafeiyu_panel
systemctl restart qqbot-astrbot        # 或者面板里点「重载插件」
```

装完后：面板 → 插件 → 「大肥鱼面板」→ **打开页面**，就能看到两个视图。

---

## 用起来

1. **打开页面**：面板 → 插件 → 大肥鱼面板 → 打开页面（手机浏览器同样能开，布局会自动变单列）。
2. **打分**：点星星（1~5 星），写一句「这种多推」「别再刷这个了」，点 💾 保存。选 5 星会自动进收藏。
3. **收藏**：卡片右上角 ⭐ 收藏，收藏的视频会单独出现在「收藏」筛选里，选题权重最高。
4. **翻日记**：顶部「她的日记本」切过去，左侧按天翻，能搜正文 / 心情 / 视频标题。

打分去哪里了：插件自己的 `plugin_data/astrbot_plugin_dafeiyu_panel/ratings.json`，
同时（如果开着 `sync_to_bili_state`）写进 `data/bili_whale/state.json` 的 `feedback[bvid] = {stars, note, fav, ts}`，
刷 B 站插件下一轮选题读这份反馈：五星、收藏的加权，低星和「别再刷」的降权。写之前会自动备份 `state.json.bak-panel`。

---

## 配置

面板 → 插件 → 大肥鱼面板 → 插件配置：

| key | 默认 | 说明 |
| --- | --- | --- |
| `enable` | true | 关掉后视图还在，但接口返回未启用 |
| `bili_state_file` | 空 | 留空自动找 `data/bili_whale/state.json` |
| `cover_dir` | 空 | 留空自动找 `data/bili_whale/covers/` |
| `journal_file` | 空 | 留空自动找 `data/whale_journal/entries.jsonl` |
| `page_size` | 24 | 打分台每页条数 |
| `allow_edit` | true | 关掉就是只读面板 |
| `sync_to_bili_state` | true | 把打分同步进刷 B 站插件的 `state.json` |
| `show_score` | true | 显示「她给 N 分」「#主题」小标签 |
| `journal_limit` | 300 | 日记最多显示多少篇 |

---

## 接口（插件视图用的）

全部挂在面板鉴权下，路由前缀 `/{plugin_name}/`：

| 方法 | 路由 | 说明 |
| --- | --- | --- |
| GET | `/{plugin}/items?page=1&size=24&filter=all&q=` | 列表 + 汇总 + 状态 |
| GET | `/{plugin}/cover?bvid=` | 单张封面，base64 |
| POST | `/{plugin}/rate` | `{bvid, stars, note, fav}` |
| GET | `/{plugin}/journal?limit=300&q=` | 日记列表 |
| GET | `/{plugin}/status` | 数据源状态（找没找到文件） |

`filter` 可选 `all / shared / unshared / fav / todo / rated`。

---

## 本地开发 / 预览

不装 AstrBot 也能看效果：

```bash
python tests/preview_server.py --port 8765 \
  --state _fixture/state.json \
  --covers _fixture/covers \
  --journal _fixture/entries.jsonl
# 浏览器打开 http://127.0.0.1:8765/她看过什么/index.html
```

预览脚本会往页面里注入一个假的 `window.AstrBotPluginView`，接口直接读本地文件。

跑测试：

```bash
python tests/test_store.py
```

---

## 已知情况

- **没有封面**：封面靠 `astrbot_plugin_bili_whale` 把图存到 `covers/<bvid>.jpg`；没存到就显示「视频已不可见 / B站取不到封面」。B 站返回 `62012`（稿件被删 / 私密 / 地区限制）的视频永远取不到封面。
- **数据是只读的**：本插件不会删你的记录，也不改 `state.json` 里的其他字段。
- **需要 AstrBot ≥ 4.29**：旧版本没有 `register_web_api`，装了也只会记一条 warning。

---

## License

MIT

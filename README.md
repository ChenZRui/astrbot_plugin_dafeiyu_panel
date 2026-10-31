# 大肥鱼面板（打分台 + 日记本 + 主人画像 + 主人教我的）

> 你的大肥鱼今晚又刷了一堆视频、写了一篇日记。
> 不用登服务器、不用再单独开个网页服务——**在 AstrBot 面板里就能看**：
> 点星星、写两句评价、点收藏，她第二天就照着你的口味挑视频。

> 另一页是她自己写的小本子：心情标签、正文、看过的视频、还有她记下的「主人教我的」。
> 再两页更狠：**她眼里的你**（性格 / 生活习惯 / 口头禅 / 心情指数 / 睡眠）和
> **主人教我的分类库**（黑话 / 梗 / 调情），你在 QQ 里教的东西自己归档。
> 四个页面都带皮肤（深海 / 纸感 / 樱花 / 森林），电脑手机都能开，布局自动变单列。

一套插件，四个视图：

| 视图（面板里的 tab） | 内容 |
| --- | --- |
| **她看过什么** | 观看历史墙：按天分组、带封面；★ 打分 / 写评价 / 点收藏；筛选「她推给我的 / 没推给我的 / 收藏 / 待我评价 / 评过的」 |
| **她的日记本** | 她写的日记：心情 pill、正文、看了哪些视频、「主人教我的」黄块、左侧按天翻 |
| **主人画像** | 她根据最近聊天总结的你：性格 / 生活习惯 / 口头禅 / 心情指数（0-10 带进度条）/ 睡眠状态 |
| **主人教我的** | 教学库：黑话 / 梗 / 调情 / 其他 四个分类，能搜、能看来源和说过几次 |

![打分台（电脑）](docs/watch.png)

![日记本（电脑）](docs/journal.png)

![主人画像](docs/profile.png)

![主人教我的](docs/lessons.png)

手机上同一个页面，KPI 两列、卡片单列、筛选换行：

<img src="docs/watch-mobile.png" width="300" alt="打分台（手机）">
<img src="docs/journal-mobile.png" width="300" alt="日记本（手机）">

---

## 这是什么 / 为什么做

「刷B站的大肥鱼」跑起来之后有个新问题：她刷了什么、给你推了什么、日记写了什么——
全都在服务器的 JSON 和 md 文件里。要看一次就得 SSH 上去，或者再单独跑一个网页服务、开隧道、记口令。

这个插件把这两件事直接搬进 **AstrBot 面板**：装完就是一个插件、两个页面，
面板自带登录和鉴权，手机浏览器打开面板也能用（如果你用 QQ 机器人，等于随手就能点评她）。

### 它是什么

- 一个**只读 + 打分**的面板插件：读另外两个插件的数据文件，渲染成面板页面；
- 你打的星和评价会写回刷B站插件的 `state.json`，**下一轮选题权重、当天投币对象都看这个**。

### 它不是什么

- 它自己**不会**刷 B站、不会写日记、不会发消息——那些是源插件干的；
- 它不改 `state.json` 里除 `feedback` 以外的任何字段（写之前自动备份 `state.json.bak-panel`）。

数据来源：

| 数据 | 来源插件 | 文件 |
| --- | --- | --- |
| 看过的视频、她给的分数、是否推给你、你打的星 | `astrbot_plugin_bili_whale`（刷B站的大肥鱼） | `data/bili_whale/state.json` 的 `seen` / `feedback` + `data/bili_whale/covers/*.jpg` |
| 日记正文、心情、看了什么、主人教了什么 | `astrbot_plugin_whale_journal`（大肥鱼日记本） | `data/whale_journal/entries.jsonl` |

**只装这一个也能用**：没有数据时页面会明确提示「还没有数据」，等你把源插件装上，刷新就有内容。

---

## 快速开始

### 方式一：插件市场（推荐）

面板 → 插件 → **插件市场** → 搜「大肥鱼面板」→ 安装 → 回插件列表点「重载」。

市场地址：<https://cloud.astrbot.app>（插件页搜 `astrbot_plugin_dafeiyu_panel`）。

### 方式二：手动放进插件目录

```bash
cd /opt/astrbot/data/plugins
git clone https://github.com/ChenZRui/astrbot_plugin_dafeiyu_panel
systemctl restart qqbot-astrbot        # 或者在面板里点「重载插件」
```

> 没有第三方依赖，不需要 pip 装东西（只用标准库 + AstrBot 自带模块）。

### 装完怎么确认

日志里会出现一行：

```
[dafeiyu-panel] 已加载｜state=…/data/bili_whale/state.json（有）｜covers=有｜journal=有
```

然后在面板：**插件 → 大肥鱼面板 → 打开页面**，顶部会有两个 tab：`她看过什么` / `她的日记本`。

---

## 用起来

### 1. 打分（影响她下一次选题）

在「她看过什么」里，每条卡片下面：

- 点星星（1~5 星）；
- 写一句评价，比如「这种多推」「别再刷这个了」；
- 点 💾 保存（或按 `Ctrl/⌘ + Enter`）。

**打 5 星会自动加进收藏**；收藏的视频在选题里权重最高。
分数落在两个地方：插件自己的 `plugin_data/astrbot_plugin_dafeiyu_panel/ratings.json`（重启不丢），
以及（开了 `sync_to_bili_state` 时）刷B站插件的 `state.json` → `feedback[bvid] = {stars, note, fav, ts}`。

### 2. 只看她的、或只看你没评的

顶部筛选：

| tab | 看什么 |
| --- | --- |
| 她推给我的 | 她这一轮真的发过给你的（`shared=true`） |
| 没推给我的 | 她看过但没选中的（用来判断她的口味准不准） |
| 收藏 | 你点过收藏 / 打了 5 星的 |
| 待我评价 | 还没打分的 |
| 评过的 | 已经打过分的 |

### 3. 日记页

「她的日记本」：左边按天翻（手机上变横向滑条），右边一天里的几篇，
每篇有心情 pill、正文、「主人教我的」黄底块、看了哪些视频、时间与对话句数。
搜索框能搜正文 / 心情 / 视频标题 / 主人教的事。

### 4. 主人画像

「主人画像」把她从聊天里总结出来的你摊开：心情指数（0-10 配一条进度条）、睡眠质量、
性格 / 生活习惯 / 口头禅三组标签，最下面是 120 字以内的总结，还标了覆盖了几天聊天、什么时候算的。

数据来自配套的「鲸鱼日记」插件（`astrbot_plugin_whale_journal`）：她每次写完日记顺手更新一次画像，
所以这个页面**需要一起装日记插件**才有内容；也可以让主人在 QQ 里发 `/主人画像` 立刻算一次。
页面读的是 `whale_journal/owner_profile.json`。

### 5. 主人教我的

「主人教我的」是分类教学库：`黑话` / `梗` / `调情` / `其他` 四个 tab，能搜索、看每条是哪天教的、
在聊天里说过几次。主人在 QQ 里直接说「记住，这是黑话：你这波真的典」，
日记插件的分类器就会把它归进「黑话」并写进 `whale_journal/lessons.json`；
用 `/教我 梗 急了急了` 也行。这个页面同样需要日记插件。

### 6. 皮肤

四个页面右上角都有皮肤切换：**深海**（默认深色）、**纸感**（暖白）、**樱花**（粉白）、**森林**（墨绿）。
选择存在浏览器 localStorage 里，四个页面共用一套，换页面不会跳回默认。

### 7. 手机怎么用

面板本身就是响应式的：手机浏览器登录面板 → 插件 → 大肥鱼面板。
视图在 390px 宽下会自动变成两列 KPI + 单列卡片，星星、评价框、收藏都能直接点。

### 8. 不打开面板也能打分（可选）

如果你还装着 `astrbot_plugin_bili_whale`，在 QQ 里发 `/打分` 也行
（`/打分 3 5 这种多推` 是「第 3 条 5 星」的意思），它会把结果写进同一份 `feedback`。

---

## 打分怎么影响选题

刷B站插件每轮选题时读 `state.json` 的 `feedback`：

- 你打 **5 星 / 收藏** → 同类主题在候选池里加权（`feedback_boost`，默认 3.0）；
- 你打 **1~2 星**、或在评价里写「别再刷」→ 降权（`feedback_penalty`，默认 5.0）；
- 每天投币只投给「你打星最高、当天还没投过」的那条。

所以：**想让什么变多，就 5 星 +「这种多推」；想让它消失，就 1 星 +「别再刷这个了」。**

---

## 配置

面板 → 插件 → 大肥鱼面板 → 插件配置：

| key | 默认 | 说明 |
| --- | --- | --- |
| `enable` | `true` | 关掉后视图还在，但接口返回「未启用」 |
| `bili_state_file` | 空 | 留空自动找 `data/bili_whale/state.json` |
| `cover_dir` | 空 | 留空自动找 `data/bili_whale/covers/` |
| `journal_file` | 空 | 留空自动找 `data/whale_journal/entries.jsonl` |
| `page_size` | `24` | 打分台每页条数 |
| `allow_edit` | `true` | 关掉就是纯只读面板 |
| `sync_to_bili_state` | `true` | 把打分同步进刷B站插件的 `state.json` |
| `show_score` | `true` | 显示「她给 N 分」「#主题」小标签 |
| `journal_limit` | `300` | 日记最多加载多少篇 |

> 三个路径键留空就好——它按 AstrBot 的标准数据目录自动定位，**换服务器/改目录都不用手填**。

---

## 接口（视图背后用的）

所有接口都在面板鉴权之下，实际地址是 `/api/v1/plugins/extensions/<plugin>/<endpoint>`：

| 方法 | endpoint | 参数 | 说明 |
| --- | --- | --- | --- |
| GET | `items` | `page` `size` `filter` `q` | 列表 + 汇总 + 数据源状态 |
| GET | `cover` | `bvid` | 单张封面，返回 base64（面板 iframe 拿不到服务器文件） |
| POST | `rate` | `{bvid, stars, note, fav}` | 打分 / 收藏 |
| GET | `journal` | `limit` `q` | 日记列表 + 按天索引 |
| GET | `profile` | — | 主人画像（性格/习惯/口头禅/心情/睡眠） |
| GET | `lessons` | `q` `limit` | 教学库（黑话/梗/调情/其他 分组） |
| GET | `status` | — | 三个数据文件在不在 |

`filter` 可选：`all / shared / unshared / fav / todo / rated`。

---

## 目录结构

```
astrbot_plugin_dafeiyu_panel/
  metadata.yaml            市场元信息（author/name/version 必须和市场记录一致）
  _conf_schema.json        面板配置项
  main.py                  插件入口：注册 5 个接口 + 页面 + /大肥鱼面板 命令
  core/store.py            读写 state.json / entries.jsonl / ratings.json（utf-8-sig + 原子替换）
  views/她看过什么/index.html    打分台（目录名 = 面板 tab 标题）
  views/她的日记本/index.html    日记本
  tests/preview_server.py  不装 AstrBot 也能看效果的本地预览
  tests/test_store.py      30 条单元测试
  docs/                    截图
```

---

## 本地开发 / 预览

不装 AstrBot 也能把界面跑起来（用一份假数据）：

```bash
python tests/preview_server.py --port 8765 \
  --state  _fixture/state.json \
  --covers _fixture/covers \
  --journal _fixture/entries.jsonl

# 浏览器打开 http://127.0.0.1:8765/
```

预览服务器会往页面里注入一个假的 `window.AstrBotPluginView`，接口直接读本地文件，
所以打分也会写进临时目录，不会污染真实数据。

跑测试：

```bash
python tests/test_store.py     # 30 passed
```

---

## 踩坑清单

都是我们真踩过、调试到凌晨的：

- **面板 tab 标题 = `views/` 下的目录名**。AstrBot 没有 `page.json` 这种元信息机制，
  `discover_plugin_pages()` 只按 `views/<dir>/index.html` 生成页面、直接把目录名当标题。
  所以想要中文标题，就把目录直接命名成中文（本插件就是这么干的），别指望在配置里改。
- **`register_web_api` 的路由必须带插件名前缀**（`/{plugin_name}/items`），否则匹配不到；
  handler 里用 `from astrbot.api.web import request, json_response, error_response`。
- **面板 iframe 里没有服务器文件权限**。封面别直接给路径，要读成 base64 从接口吐出来。
- **前端 bridge 是 `window.AstrBotPluginView`**（老别名 `AstrBotPluginPage`）：
  `ready()` / `apiGet(endpoint, params)` / `apiPost(endpoint, body)`，
  endpoint **不带前导斜杠也不带 query**；返回 `{status:"ok",data}` 时 bridge 直接给你 `data`。
- **AstrBot ≥ 4.29** 才有 `register_web_api`；更老的版本装了只会记一条 warning、没有页面。
- `state.json` / `entries.jsonl` 可能是 **UTF-8 with BOM**，一律用 `utf-8-sig` 读。
- 写回 `state.json` 要**原子替换**（临时文件 + `os.replace`），并且先备份 —— 那是源插件正在用的活文件。
- 时间戳在 `state.json` 里有时是数字、有时是字符串，解析两种都要兼容，别直接 `float()`。

---

## 已知情况 / FAQ

**卡片显示「视频已不可见 / B站取不到封面」**
封面是源插件缓存到 `data/bili_whale/covers/<bvid>.jpg` 的，没缓存到就显示占位。
B站 返回 `62012`（稿件已删 / 转私密 / 地区限制）的视频**永远**取不到封面，点「去B站打开」也可能打不开，这类可以忽略。

**页面打开是空的 / 提示还没有数据**
先看面板 → 插件 → 大肥鱼面板 → 配置里的三个路径，或者直接看 `/status` 接口。
源插件没装、或数据目录不在默认位置、或 `enable` 被关了，都会这样。

**打了分但她的选题没变**
① 确认 `sync_to_bili_state` 是开的；② 确认写的是刷B站插件正在读的那份 `state.json`
（`bili_state_file` 留空时自动找，如果你手动改过它的路径，这里也要对上）；③ 权重不是立刻生效，
她下一轮选题时才读。

**市场装完没看到页面**
点一次「重载插件」，还不行就 `systemctl restart`。日志里没有 `[dafeiyu-panel] 已加载` 就是没加载成功。

**会不会把她的数据弄坏**
本插件只在 `rate` 时写 `feedback[bvid]`，写前备份 `state.json.bak-panel`，其余字段一律不动。

---

## 风险与合规

- 数据来自你自己的 AstrBot 实例，本插件不发任何网络请求、不上传任何内容。
- 「刷B站」这件事本身的风险（频率、风控、账号协议）属于源插件，见那个仓库的说明。
- 建议只在自己的面板里开，别把带个人日记的面板对公网敞开。

## License

MIT

---

## 更新日志

### v1.1.1（2026-10-31，修 bug）

- **修**：`lessons.json` / `entries.jsonl` 里时间戳写成 ISO 字符串时，面板接口会抛
  `could not convert string to float`，「主人教我的」整页打不开。现在两种写法都能读。
- **修**：日记 LLM 偶尔返回坏 JSON（正文里带没转义的双引号），以前会把整段
  `{"mood": ...}` 当正文写进日记；现在会逐字段捞回来，页面不再显示一坨花括号。
- **修**：深色皮肤下日记页的标题、按天小标题、视频列表文字看不见（写死了浅色主题的颜色）。
- **新增**：独立站（`watchui.py` 那一套，双击 bat 打开的那个）现在**和面板共用同一份视图 HTML**，
  通过 `panel_pages.py` 把 `window.AstrBotPluginView` 桥接到 `/__api/...`。以后加页面只改一处，
  两边同时生效；首页也变成了四个入口的菜单。

### v1.1.0

- 新增两个视图：**主人画像**（心情指数进度条、睡眠、性格/习惯/口头禅标签、总结）
  和 **主人教我的**（黑话 / 梗 / 调情 / 其他 四类教学库，可搜索）。
- 新增 `profile` / `lessons` 两个接口，状态接口多了 `profile_exists` / `lessons_exists`。
- 四个页面都加了**皮肤切换**（深海 / 纸感 / 樱花 / 森林），选中的皮肤存在浏览器里。
- 修了深色主题下 tab 与导航选中态「白字白底」看不清的问题；手机窄屏下 tab 换行不再溢出。
- 依赖说明：画像和教学库的数据由配套的 `astrbot_plugin_whale_journal`（鲸鱼日记）生成；
  没装的话这两页会提示「还没接过」，打分台与日记本不受影响。

### v1.0.0

- 首个版本：打分台 + 日记本两个视图，封面 base64、打分/评价/收藏、按天索引。

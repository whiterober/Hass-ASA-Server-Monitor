# dino-import 资讯广场底部来源链接（`lb-news-links`）

## 结构
`LB_NEWS.tabs[i].links`（或 `children[j].links`）数组，渲染落在 `lbNewsRender()` 末尾，生成 `#lbNews .lb-news-links`。
已删除所有「在新窗口打开」跳转链接（v5946），只保留这里的底部来源入口。

## 当前来源链接权威表（v5954，2026-11-02）
| 一级 Tab | 子 Tab | 入口 |
|---|---|---|
| PC版本 | — | Discord `1219676794840547388/...`（PC 下载等） |
| 新闻 | — | Discord `1219676794840547388/1239938054328684657` |
| ADM | ADM版本 | Discord `1219676794840547388/...` |
| ADM | 预告 | Discord `1219676794840547388/1219684258298200224` |
| **汉化** | — | **飞书** `https://my.feishu.cn/wiki/ZipZwbSwZipThMkiFrHcibeCn6e`（v5954 替换掉原「贴吧 + 123网盘」） |
| API | API版本 | `https://ark-server-api.com/resources/categories/ark-survival-ascended.2/` + Discord `1219408563122999356/1219419717694001313` |
| API | API缓存 | 同上 ASA API + Discord `1219408563122999356/1243622513779675186` |

## 图标规则
- **Discord 不能用 `mdi-discord`**（字体 glyph 缺失：`width=0`、`::before content=none`）→ 用内联 SVG 常量 `LB_SVG_DISCORD`（官方 MDI path，891 字符），渲染成 `<svg width=15 height=15>`
- 其他图标先探测再选：注入 `<span class="mdi mdi-xxx">` 读 `getBoundingClientRect().width`，`w>5` 才可用
- 飞书文档用 `mdi-file-document-outline`（实测 19px 正常）

## 注意
`api_ver` / `api_cache` 频道里若只有**转发消息**，Discord API 不返回正文 → 页面显示「本条公告仅包含频道标题」。需让用户把内容**复制成普通消息**发到频道。

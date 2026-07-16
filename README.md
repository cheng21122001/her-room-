# 与她的房间 · In Her Room

聚焦女性罪犯的真实犯罪案例档案网站。黑白剪影视觉，只读展示，
数据以代码形式存放在仓库中（`seed_data.py`），网站启动时自动重建数据库。

线上地址：https://her-room.onrender.com

## 本地运行

```bash
cd her-room
source .venv/bin/activate   # 首次：python3 -m venv .venv && pip install -r requirements.txt
python app.py               # 打开 http://127.0.0.1:5001
```

或直接双击 `启动网站.command` / `停止网站.command`。

## 如何添加 / 修改案例

1. 打开 `seed_data.py`，复制一个现有条目，修改各字段（说明见下）
2. 运行校验：`python validate.py`（必须显示 OK）
3. 提交并推送：`git add -A && git commit -m "..." && git push`
4. Render 会自动重新部署，几分钟后线上生效

### 字段说明

| 字段 | 说明 |
|---|---|
| `archive_no` | 档案编号，格式 `HR-001`，全局唯一，按录入顺序递增 |
| `name` / `aliases` | 姓名 / 别名、绰号 |
| `period` | 案发时间段的展示文本，如 `1989–1990年` |
| `era` | 年代分类（用于筛选），如 `20世纪90年代` |
| `region` | 地区分类（用于筛选），如 `美国` `英国` |
| `year_start` | 案发起始年份（整数，用于时间线排序） |
| `location` | 具体地点 |
| `case_type` | 案件类型（用于筛选） |
| `credibility` | 司法结果 / 史料可信度标注，如 `已定罪` `未定罪 · 悬案` `史料存争议` |
| `symbol` | 象征符号：`tower` `envelope` `gun` `road` `flame` `tape` `house` `camera` `shovel` `poison` |
| `summary` | 一句话简述（列表卡片显示） |
| `case_details` | 完整案情记述（详情页折叠展开） |
| `timeline` | 结构化时间线：`[("时间", "事件"), ...]` 按时间顺序 |
| `psychological_profile` | 心理 / 动机侧写 |
| `terms` | 关联词汇表词条 id 列表，词条定义在 `seed_data.py` 底部 `GLOSSARY` |
| `sources` | 资料来源（书籍 / 庭审记录 / 纪录片等） |

### 新增词汇表词条

在 `seed_data.py` 底部的 `GLOSSARY` 中添加 `{id, term, term_en, definition}`，
然后即可在案例的 `terms` 中引用其 `id`。

## 页面结构

- `/` 开场页（黑白分割 · 推门而入）
- `/overview` 总览仪表盘（馆藏数字 · 最新收录 · 分布图）
- `/archive` 档案列表（关键词检索 + 年代/类型/地区筛选）
- `/case/<id>` 案例详情（黑白条带交替 · 事件时间轴 · 相关档案）
- `/timeline` 全部案例的年代总览
- `/network` 关系网络图（同类型 / 同地区 / 共同词条连线）
- `/stats` 馆藏统计
- `/glossary` 词汇表
- `/capture` 录入工具（表单生成 seed_data.py 代码片段，不直接写库）
- `/export.json` `/export.csv` 全量数据导出
- `/random` 随机翻开一份档案

## 部署

推送到 GitHub `main` 分支即自动触发 Render 部署（配置见 `render.yaml`）。
数据库无持久化需求：每次启动都由 `seed_data.py` 重建，仓库即唯一数据源。

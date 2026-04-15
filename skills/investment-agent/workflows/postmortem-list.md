# Postmortem List Workflow

## Goal

查看和管理 Mistake Memory 的 draft / active / retired 条目。

## Preferred tool

```bash
python app/tools/postmortem_tools.py --list
```

也可按状态过滤：

```bash
python app/tools/postmortem_tools.py --list --status draft
```

## Steps

### 1. 读取全部条目

默认读取全量条目。

### 2. 按状态分组展示

建议至少分成三组：
- Draft：待审核
- Active：生效中
- Retired：已归档

### 3. 对 draft 给出下一步提示

对 draft 条目，提醒用户：
- 需要 approve 才会在 self-check 中生效
- 不再需要的可 retire

可直接执行：

```bash
python app/tools/postmortem_tools.py --approve <ID>
python app/tools/postmortem_tools.py --retire <ID>
```

### 4. 对 active 展示最重要的信息

对 active 条目，至少展示：
- 类型
- 严重度
- trigger_check
- prevention_rule

### 5. 输出 summary

汇总：
- 总记录数
- draft / active / retired 各多少条
- 若 active 为 0，应提示先创建并激活第一条教训

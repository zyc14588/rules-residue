<!-- SECTION-ID: R2-INTEGRATION-INSTALLATION -->
# R2 权威设计包安装策略

## 禁止直接覆盖

`01_REPO_OVERLAY/` 不是一个可以直接 `cp -r` 覆盖目标仓库的补丁。Codex 必须先检查 M1 实际路径、生成文件边界和当前权威入口。

## 推荐集成模式

### 1. 新增隔离目录

优先将 R2 自然语言权威放入：

```text
docs/authority/r2/
```

将R2机器源放入：

```text
governance/r2/
```

将R2新增Schema放入：

```text
schemas/r2/
```

将R2创作源内容合并到M1既有：

```text
authoring/story/
authoring/world/
authoring/characters/
authoring/equipment/
authoring/mysteries/
authoring/art/
```

### 2. 只更新单一现行入口

Codex根据仓库事实选择**一个**权威入口增加R2导航：

- 若 `README.md` 是项目权威入口，只添加短导航；
- 若 `docs/authority/00_*` 是权威入口，则更新该文件；
- 若入口是生成文件，必须修改机器源并通过 `projectctl generate` 生成，不得手工编辑。

不得在多个入口复制整套R2正文。

### 3. 机器决策并行期

若现有 `governance/decisions.json` / `DECISION_REGISTER.yaml` 有固定Schema：

1. 先安装 `governance/r2/decisions.r2.yaml` 作为隔离的R2机器源；
2. 增加可验证导入/映射规则；
3. 只有在现有Schema能无损表达 `R2-A01—R2-J24` 后才合并；
4. 不能表达的字段进入Schema变更任务，禁止丢弃修订说明。

### 4. authoring内容合并

M1原先将终极真相保持OPEN；R2已关闭这些OPEN项。安装时必须：

- 更新 Story Bible、Truth Bible、Mystery Graph、Return Home Arc和Reveal Policy；
- 将旧OPEN标记为 `SUPERSEDED_BY_R2`；
- 保留历史记录，不允许两个冲突真相同时标记权威；
- 继续保持GM-only真相不进入玩家runtime包。

### 5. game-package保持不变

R2权威安装批次不应实现M2运行内容，也不应修改：

```text
game-package/**
package.lock.*
dist/**
```

只有R2权威安装独立验收通过后，M2施工批次才把相应语义转为runtime结构。

## 安装完成判据

```text
R2_AUTHORITY_FILES_INSTALLED=PASS
R2_MACHINE_REGISTRY_VALID=PASS
R2_DECISION_COUNT_191=PASS
R2_SECTION_IDS_UNIQUE=PASS
M1_OPEN_TRUTHS_SUPERSEDED=PASS
PLAYER_GM_MECHANICAL_LAYERS_SEPARATED=PASS
NO_GAME_PACKAGE_RUNTIME_CHANGE=PASS
NO_PLATFORM_REPO_CHANGE=PASS
CURRENT_ACCEPTANCE_BASELINE_STILL_PASS=PASS
```

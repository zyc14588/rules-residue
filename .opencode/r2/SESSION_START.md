<!-- SECTION-ID: R2-OPENCODE-SESSION-START -->
# OpenCode Session Start

你是《规则残差》的脚本执行者，不是游戏设计者。

## 必需输入

必须收到合法Task Packet：

```text
task_id
authority section refs
input paths + sha256
allowed_paths
forbidden_paths
open/deferred decisions
acceptance
expected_outputs
```

缺一即返回 `BLOCKED_INPUT`。

## 只读

只读取Task Packet列出的文件和Section。不得递归读取：

```text
docs/**
authoring/**
governance/**
full Truth Bible
campaign seed manifest
unrelated modules
```

## 禁止

- 修改权威设计、Schema、治理、计划、美术；
- 发明规则、代价、真相、NPC动机或结局；
- 使用未声明网络、文件系统、时钟、环境变量、进程、动态库、debug API；
- 将Lua全局变量作为权威持久状态；
- 读取其他玩家私有视图；
- 把自测写成最终PASS。

<!-- SECTION-ID: R2-AUTH-M1-INTEGRATION -->
# M1 工程基础集成契约

## 复用而非重建

R2必须建立在M1已有的：

- `authoring/`创作源；
- Region / Rule Domain / Arc / Module / NPC / Faction / Clue模板；
- 注册表驱动Module验证；
- `game-package/`运行输入边界；
- `workflow/queue/`与Task Packet；
- Codex → OpenCode/Grok → Codex集成链；
- `projectctl`渐进披露路由；
- 独立验收流程。

不得创建另一套平行 `r2-authoring/`、另一种Module注册表或新的非兼容Task Packet。

## M1 OPEN关闭传播

M1为防止实现者代替所有者做决定，曾将最终世界真相、规则来源与归乡条件保持OPEN。R2已经冻结这些内容。安装必须：

1. 找到所有对应OPEN项；
2. 标记 `SUPERSEDED_BY_R2`；
3. 将Truth Bible、Mystery Graph、Return Home Arc和Reveal Policy更新到R2；
4. 保持玩家/主持/机械可见性分离；
5. 增加负向测试证明GM真相未进入玩家包或普通AI上下文。

## 数据映射

| M1对象 | R2扩展 |
|---|---|
| Region | 大区观测/解决/永久稳定、逻辑异常区、大区独特规则、Boss影响 |
| Rule Domain | 层级、权限、豁免协议、即时/长期效果、残差、跨循环、碰撞类别 |
| Arc | 求生/建模/干预/终局软阶段与非线性条件 |
| Module | 一个可运行内容单元，不等于大区、Campaign或完整循环 |
| NPC/Faction | 公开/真实/自我认知/错误认知、阵营应对方案和跨循环关系 |
| Clue/Hypothesis/Revelation | 已知信息、因果关系网、六区观测和功能性终局诊断 |
| Art brief | 纯2D、声部、异常层级、可访问性、来源和红线标签 |

## 施工边界

权威安装批次只修改文档、机器登记、Schema草案和authoring源，不修改runtime包。M2批次再按规格优先顺序生成Schema、fixture、Lua、资产和注册Module。

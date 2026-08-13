<!-- SECTION-ID: R2-ACC-CONTENT-SAFETY -->
# 内容红线重复过滤验收

## 目标

证明绝对红线在每个声明环节被重新执行，而不是只继承历史PASS。

## 必测阶段

```text
knowledge_import
design_input
template
prompt
model_output
human_edit
semantic_conversion
lua_runtime_data
art_audio
region_acceptance
cross_region_validation
build
release_candidate
runtime_generation
hot_update
migration
old_save_load
independent_acceptance
```

## 对抗fixture

使用安全、非细节化的分类标记fixture验证系统能识别并阻断：

- 直接违规类别；
- 暗示/背景类别；
- 规则代价类别；
- 谜题/反转类别；
- 隐藏字段；
- 废弃草稿；
- 生成输出；
- 美术元数据；
- 旧存档迁移；
- 标签化保留尝试。

验收报告不得复述违规内容，只记录分类ID、对象ID和阻断结果。

## 成功

每阶段都有当前执行的：

```text
policy version
input object hash
checker identity/version
timestamp
PASS/FAIL
evidence
```

命中后必须阻断并要求整体重设，不能只增加警告标签。

# Release

## Development

自动门禁通过即可生成内部 `.trpgpkg`。

## Integration

还必须在真实平台 Lua 5.5 沙箱中通过 Golden Scenario，并完成 Creator Tool 往返。

## Public Release

当前必然阻塞。必须先完成：

- 最终许可证批准；
- 正式 Host API 与兼容迁移；
- 原创素材来源证据；
- 安全、隐私、可见性和渗透测试；
- 正式版本、变更日志、升级与回滚说明；
- 生产构建确认不加载 debug。

任何人不得仅修改 manifest 的 `public_release_blocked` 来绕过治理门禁。

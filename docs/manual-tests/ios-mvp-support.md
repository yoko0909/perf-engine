# iOS MVP 手动验收清单

## 验收环境

- [ ] Windows 主机可以运行 PerfEngine 工具包。
- [ ] iPhone 通过 USB 连接到 Windows 主机。
- [ ] iPhone 已解锁，并且已在弹窗中信任当前电脑。
- [ ] iPhone 上已安装待测 App。
- [ ] 待测 App 可手动启动并保持前台运行。

## 工具链依赖

- [ ] 验证用户本机不需要预先安装 `go-ios`、`sib` 或 `pymobiledevice` CLI。
- [ ] 验证 iOS 设备发现、App 列表和 iOS 17+ tunnel 均通过打包内 Python 依赖 `pymobiledevice3` 工作，不依赖 `assets/ios/ios.exe` 或 `assets/ios/sib.exe`。
- [ ] 验证从普通终端启动 PerfEngine 时，iOS 设备发现不依赖用户 PATH 中的外部 iOS CLI。

## pymobiledevice3 9.0.0 基线

- [x] Windows 环境需要 `pywin32`；缺少时 `pymobiledevice3.lockdown` 会因为 `win32security` 缺失而导入失败。
- [x] `pymobiledevice3==9.0.0` 已验证可以导入 `pymobiledevice3.lockdown` 和 `win32security`。
- [x] 9.0.0 的核心 API 是 async：`usbmux.list_devices`、`create_using_usbmux`、service `connect()`、`get_apps()`、`get_battery()`、DVT 调用均需要 await。
- [x] 9.0.0 使用 `DvtProvider` 作为 DVT 入口；Demo 4.2.3 的 `DvtSecureSocketProxyService` 路径不可用。
- [x] 当前 USB 真机 baseline：UDID `00008110-000E699901A2801E`，ProductVersion `15.0`，ProductType `iPhone14,5`。
- [x] 已验证 `InstallationProxyService.get_apps('User')` 可返回用户 App 列表。
- [x] 已验证 `DiagnosticsService.get_battery()` 可返回 `CurrentCapacity`、`Voltage`、`InstantAmperage`、`Temperature` 等字段。
- [x] 已验证 `DvtProvider + ProcessControl` 可查询目标 App PID。
- [x] 已验证 `Sysmontap.create(dvt)` 可返回目标进程 row，包含 `physFootprint`、`memResidentSize`、`cpuTotalUser`、`cpuTotalSystem` 等字段。
- [ ] CoreProfile/FPS 仅确认能返回原始 bytes；Demo 的 `code == 830472984` 事件码在当前样本中未命中，仍需单独确认 FPS 来源。

## 主流程

- [ ] 启动 PerfEngine。
- [ ] 点击刷新设备。
- [ ] 设备列表中出现 iPhone，且设备项显示 `[ios]`。
- [ ] 选择 iPhone。
- [ ] App 列表加载成功。
- [ ] App 列表中能看到待测 App。
- [ ] 手动启动待测 App，并保持 App 运行。
- [ ] 在 PerfEngine 中选择待测 App。
- [ ] 点击 Start。
- [ ] 采集开始后，设备和 App selector 被锁定。
- [ ] 状态区域显示 running 或明确的 iOS 状态提示。
- [ ] FPS 图表开始出现数据，或在数据暂未到达时显示等待提示。
- [ ] Frame Time 图表开始出现数据，或缺失时保持空点/断线。
- [ ] App CPU 图表开始出现数据，或缺失时保持空点/断线。
- [ ] Total CPU 图表开始出现数据，或缺失时保持空点/断线。
- [ ] Memory 图表使用 iOS `physFootprint` 口径，或缺失时保持空点/断线。
- [ ] Temperature 图表开始出现数据，或单位未验证/不可用时保持空点/断线。
- [ ] 点击 Stop。
- [ ] 采集停止后，设备和 App selector 恢复可操作。

## 异常流程

- [ ] 采集中断开 iPhone USB 连接。
- [ ] PerfEngine 显示明确的设备断连状态。
- [ ] 断连后轮询停止，selector 恢复可操作。
- [ ] 重新连接 iPhone 并点击刷新设备。
- [ ] iPhone 可以重新出现并再次选择。
- [ ] 采集中退出目标 App。
- [ ] PerfEngine 显示目标 App 已退出或不可采集的状态。
- [ ] App 退出后轮询停止，selector 恢复可操作。
- [ ] 重新启动目标 App 后可以再次 Start。
- [ ] 未信任电脑时，PerfEngine 显示需要解锁 iPhone 并信任电脑的提示。
- [ ] 缺少 `pymobiledevice3` 或 Windows `pywin32` 支持时，PerfEngine 显示工具包缺失提示，而不是 Python/Node 栈信息。

## 指标观察记录

| 指标 | 期望口径 | 真机观察结果 | 备注 |
| --- | --- | --- | --- |
| FPS | iOS FPS collector 或 CoreAnimation FPS | 暂无真实数据 | CoreProfile 原始 bytes 可返回，但 Demo 的 `830472984` 事件码尚未命中。 |
| Frame Time | 优先逐帧数据；没有逐帧数据时使用 `1000 / FPS` | 暂无真实数据 | 依赖 FPS 或逐帧数据源；当前同样被 `InvalidService` 阻塞。 |
| App CPU | 目标 App 进程 CPU | 暂无真实数据 | 通过 `pymobiledevice3` DVT/Sysmontap 读取。 |
| Total CPU | 系统总 CPU | 暂无真实数据 | 通过 `pymobiledevice3` DVT/Sysmontap 读取。 |
| Memory | `physFootprint`，不使用 virtual memory 替代 | 暂无真实数据 | 需要从 system/perfmon/DVT 数据中确认字段来源。 |
| Temperature | battery temperature；单位未确认时允许为空 | `pymobiledevice3` Diagnostics 可返回原始电池字段 | 已观察到 `CurrentCapacity`、`Voltage`、`Temperature` 等字段；温度单位仍需确认，未确认前 UI 不应伪造成有效摄氏度。 |

## 当前真机验证结果

- [ ] `pymobiledevice3.usbmux.list_devices()` 可以发现 iPhone。
- [ ] 设备下拉框可以显示 iPhone。
- [ ] `pymobiledevice3` `InstallationProxyService.get_apps('User')` 可以返回用户 App 列表，且 PerfEngine 的 App 下拉框可以显示 App。
- [ ] iOS 17+ 设备需要 tunnel 时，PerfEngine 可通过进程内 `pymobiledevice3.tunneld.server.TunneldRunner` 启动 tunnel。
- [x] 点击 Start 后 UI 有响应，Session 可以进入 running/等待数据状态。
- [ ] 点击 Start 后真实性能采集尚未可用，Session Status 仍显示 `Waiting for ios data.`。
- [ ] FPS、Frame Time、App CPU、Total CPU、Memory 图表当前为空。
- [ ] 目标 App 状态当前不会随 App 退出/不可采集而变化。
- [ ] 若 DVT 服务不可用，需要记录 `pymobiledevice3` 返回的 operator-safe 错误，并确认 UI 不暴露原始 traceback。

## 验收分工

- [ ] 真机测试由用户执行。
- [ ] 开发侧根据真机测试反馈记录指标口径差异。
- [ ] 开发侧根据真机测试反馈修复设备连接、App 列表、采集启动、状态提示或指标映射问题。

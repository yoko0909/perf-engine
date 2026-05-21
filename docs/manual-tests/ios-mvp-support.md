# iOS MVP 手动验收清单

## 验收环境

- [ ] Windows 主机可以运行 PerfEngine 工具包。
- [ ] iPhone 通过 USB 连接到 Windows 主机。
- [ ] iPhone 已解锁，并且已在弹窗中信任当前电脑。
- [ ] iPhone 上已安装待测 App。
- [ ] 待测 App 可手动启动并保持前台运行。

## 工具链依赖

- [ ] 验证用户本机不需要预先安装 `go-ios`、`sib` 或 `pymobiledevice` CLI。
- [ ] 验证工具包内存在 `assets/ios/ios.exe`。
- [ ] 验证工具包内存在 `assets/ios/sib.exe`。
- [ ] 验证从普通终端启动 PerfEngine 时，iOS 设备发现不依赖用户 PATH。

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
- [ ] 缺少内置 iOS 工具时，PerfEngine 显示工具包缺失提示，而不是 Python/Node 栈信息。

## 指标观察记录

| 指标 | 期望口径 | 真机观察结果 | 备注 |
| --- | --- | --- | --- |
| FPS | iOS FPS collector 或 CoreAnimation FPS | 暂无真实数据 | `sib perfmon -u <udid> -b <bundleId> --fps ... -j -r 1000` 当前返回 `InvalidService`。 |
| Frame Time | 优先逐帧数据；没有逐帧数据时使用 `1000 / FPS` | 暂无真实数据 | 依赖 FPS 或逐帧数据源；当前同样被 `InvalidService` 阻塞。 |
| App CPU | 目标 App 进程 CPU | 暂无真实数据 | 依赖 iOS 性能服务；当前 `sib perfmon` 无法启动。 |
| Total CPU | 系统总 CPU | 暂无真实数据 | 依赖 iOS 性能服务；当前 `sib perfmon` 无法启动。 |
| Memory | `physFootprint`，不使用 virtual memory 替代 | 暂无真实数据 | 需要从 system/perfmon/DVT 数据中确认字段来源。 |
| Temperature | battery temperature；单位未确认时允许为空 | `sib battery` 可返回原始电池字段 | 已观察到 `CurrentCapacity`、`Voltage`、`Temperature` 等字段；温度单位仍需确认，未确认前 UI 不应伪造成有效摄氏度。 |

## 当前真机验证结果

- [x] 工具包内已存在 `assets/ios/ios.exe` 和 `assets/ios/sib.exe`。
- [x] `ios.exe list --details` 可以发现 iPhone；输出中会先出现 go-ios agent/tunnel warning，再返回 `deviceList`。
- [x] 设备下拉框可以显示 iPhone。
- [x] `sib.exe app list -u <udid> -j` 可以返回用户 App 列表，且 PerfEngine 的 App 下拉框已经可以显示 App。
- [x] 点击 Start 后 UI 有响应，Session 可以进入 running/等待数据状态。
- [ ] 点击 Start 后真实性能采集尚未可用，Session Status 仍显示 `Waiting for ios data.`。
- [ ] FPS、Frame Time、App CPU、Total CPU、Memory 图表当前为空。
- [ ] 目标 App 状态当前不会随 App 退出/不可采集而变化。
- [ ] `sib.exe ps -u <udid>` 当前返回 `InvalidService`，提示可使用 `sib mount` 修复。
- [ ] `sib.exe mount -u <udid>` 当前尝试下载 Developer Disk Image 失败。
- [ ] 需要先解决 Developer Disk Image/DDI 或 DVT 服务可用性，再继续接入真实 perf collector。

## 验收分工

- [ ] 真机测试由用户执行。
- [ ] 开发侧根据真机测试反馈记录指标口径差异。
- [ ] 开发侧根据真机测试反馈修复设备连接、App 列表、采集启动、状态提示或指标映射问题。

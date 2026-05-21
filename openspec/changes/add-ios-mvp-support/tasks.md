## 1. 平台模型与分发

- [x] 1.1 在 `src/perfengine/app/models.py` 中新增 `Platform` 枚举，支持 `android` 和 `ios`。
- [x] 1.2 为 `DeviceInfo`、`AppInfo`、`SessionState`、`PhoneStatus` 增加平台字段，并保持现有 Android 默认行为不变。
- [x] 1.3 新建 `src/perfengine/app/platforms.py`，实现平台注册表，负责合并设备列表并按设备 ID 查找平台。
- [x] 1.4 修改 `src/perfengine/app/service.py`，让设备发现、App 列表、采集器调用可以按平台分发。
- [x] 1.5 保留旧的 Android-only 构造方式，避免现有测试和 Android MVP 行为被破坏。
- [x] 1.6 新增 `tests/app/test_platform_dispatch.py`，覆盖 Android/iOS 设备合并、App 查询分发、采集器分发。
- [x] 1.7 更新 `tests/app/test_service.py` 中的测试夹具，补齐平台字段。
- [x] 1.8 运行 `python -m pytest tests/app/test_service.py tests/app/test_platform_dispatch.py -q`，确认服务层测试通过。
  - 已由用户在本地执行通过：`5 passed in 0.04s`。

## 2. 内置 iOS 工具链与设备发现

- [x] 2.1 新建 `src/perfengine/ios/__init__.py`，建立 iOS 后端模块目录。
- [x] 2.2 新建 `src/perfengine/ios/tooling.py`，定义产品包内置 iOS 工具路径，例如 `assets/ios/ios.exe` 和 `assets/ios/sib.exe`。
- [x] 2.3 在 `tooling.py` 中实现内置工具存在性检查，缺失时抛出 operator-safe 的 `OperatorError`。
- [x] 2.4 新增 `tests/ios/test_tooling.py`，覆盖工具路径解析和缺失资产错误。
- [x] 2.5 新建 `src/perfengine/ios/device_provider.py`，通过内置 go-ios 工具发现 Windows 主机连接的 iPhone。
- [x] 2.6 在 iOS 设备发现中解析 `go-ios list --details` 输出，生成 `Platform.IOS` 的 `DeviceInfo`。
- [x] 2.7 在 iOS 设备发现中处理工具调用失败、JSON 无效、设备未信任、无设备等错误，并转换为用户可理解的提示。
- [x] 2.8 新增 `tests/ios/test_device_provider.py`，覆盖成功解析和工具失败场景。
- [x] 2.9 运行 `python -m pytest tests/ios/test_tooling.py tests/ios/test_device_provider.py -q`，确认 iOS 工具链与设备发现测试通过。
  - 已执行通过：`python -m pytest tests/ios/test_tooling.py tests/ios/test_device_provider.py -q --basetemp=.pytest-tmp`，`7 passed in 0.04s`。

## 3. iOS Tunnel 与 App 列表

- [x] 3.1 新建 `src/perfengine/ios/tunnel.py`，实现 Windows 主机侧 iOS tunnel 管理器。
- [x] 3.2 在 tunnel 管理器中判断 iOS 17+ 等需要 tunnel 的场景。
- [x] 3.3 在 tunnel 管理器中自动启动 `go-ios tunnel start --userspace`，不要求用户手动执行命令。
- [x] 3.4 明确 tunnel 是 Windows 主机侧连接服务，不是安装到 iPhone 上的 App。
- [x] 3.5 在 tunnel 启动失败或超时时抛出 operator-safe 的 iOS 通信错误。
- [x] 3.6 新建 `src/perfengine/ios/app_provider.py`，实现选中 iPhone 后的用户 App 列表读取。
- [x] 3.7 在 App provider 中读取 iOS App 列表，并避免因 tunnel/DDI 未就绪阻塞普通 App 列表加载。
  - 真机反馈：`sib.exe app list -u <udid> -j` 不依赖 tunnel 即可返回 App 列表；因此 App 列表阶段不强制执行 tunnel 准备，真实采集阶段再准备开发者服务。
- [x] 3.8 将 iOS App 信息映射为 `Platform.IOS` 的 `AppInfo`，按显示名排序。
- [x] 3.9 新增 `tests/ios/test_app_provider.py`，覆盖准备流程和 App 字段映射。
- [x] 3.10 运行 `python -m pytest tests/ios/test_app_provider.py -q`，确认 iOS App 列表测试通过。
  - 已执行通过：`python -m pytest tests/ios/test_tunnel.py tests/ios/test_app_provider.py -q --basetemp=.pytest-tmp`，`6 passed in 0.05s`。

## 4. iOS 指标口径与归一化

- [x] 4.1 新建 `src/perfengine/ios/metrics.py`，实现 iOS 原始数据到现有 `MetricPoint` 的映射。
- [x] 4.2 将 iOS FPS collector 或 CoreAnimation FPS 映射到 `MetricPoint.fps`。
- [x] 4.3 将可靠逐帧数据或 `1000 / FPS` 映射到 `MetricPoint.frame_time_ms`。
- [x] 4.4 将 iOS system sampler 的目标 App CPU 映射到 `MetricPoint.app_cpu_percent`。
- [x] 4.5 将 iOS system sampler 的系统 CPU 映射到 `MetricPoint.total_cpu_percent`。
- [x] 4.6 将 iOS `physFootprint` 映射到 `MetricPoint.memory_mb`，不使用 virtual memory 替代主内存图。
- [x] 4.7 将 iOS battery temperature 映射到 `MetricPoint.temperature_c`，但单位未验证时允许保持 `unknown` 或 `null`。
- [x] 4.8 保留不可用或未验证指标为 `null`，禁止用 `0` 伪造数据。
- [x] 4.9 新增 `tests/ios/test_metrics.py`，覆盖 Demo 风格字段映射、缺失指标、全空样本返回 `None`。
- [x] 4.10 运行 `python -m pytest tests/ios/test_metrics.py -q`，确认指标归一化测试通过。
  - 已执行通过：`python -m pytest tests/ios/test_metrics.py -q --basetemp=.pytest-tmp`，`3 passed in 0.03s`。

## 5. iOS Sampler 生命周期

- [x] 5.1 新建 `src/perfengine/ios/sampler.py`，实现与现有 collector contract 对齐的 `begin`、`stop`、`read`。
- [ ] 5.2 在 `begin` 中执行 iOS 连接准备、App 运行状态检查、collector 启动。
  - 当前状态：接口已接入，UI 点击 Start 后会进入 running；但 `IOSClient.start_collectors()` 仍是占位实现，尚未真正启动 iOS 性能采集器。
- [x] 5.3 在 `stop` 中停止 iOS collector，并清理当前活跃会话。
- [ ] 5.4 在 `read` 中读取 iOS 状态、FPS、system、battery 数据，并调用 iOS 指标归一化。
  - 当前状态：sampler 逻辑和归一化逻辑已完成；真实 `IOSClient.read_fps_sample()`、`read_system_sample()`、`read_battery_sample()` 还未接入真实工具输出，所以真机 UI 会显示 `Waiting for ios data.` 且图表为空。
- [x] 5.5 当 iOS 样本暂未到达时返回 `point=None`，并在 `PhoneStatus.status_notice` 中提示“等待 iOS 数据”。
- [x] 5.6 当部分 iOS 指标不可用时保持会话 running，并通过 `status_notice` 提示“部分 iOS 指标不可用”。
- [ ] 5.7 当 iPhone 断连、目标 App 退出、启动失败时，返回明确 session 状态或 operator-safe 错误。
  - 当前状态：sampler 有对应状态分支和测试；但真实 `IOSClient.get_phone_status()` 仍返回占位 running 状态，尚不能检测目标 App 退出或设备断连。
- [x] 5.8 新增 `tests/ios/test_sampler.py`，覆盖 begin/read/stop、等待数据、部分指标缺失、App 退出。
- [x] 5.9 运行 `python -m pytest tests/ios/test_sampler.py tests/ios/test_metrics.py -q`，确认 sampler 测试通过。
  - 已执行通过：`python -m pytest tests/ios/test_sampler.py tests/ios/test_metrics.py -q --basetemp=.pytest-tmp`，`8 passed in 0.03s`。

## 6. 应用组装与后端集成

- [ ] 6.1 新建 `src/perfengine/ios/client.py`，作为 iOS 后端 facade，封装工具链、tunnel、App 列表、collector 读写接口。
  - 当前状态：工具链、设备发现、App 列表 facade 已可用；collector 启停、状态读取、FPS/system/battery 读取仍需接入真实实现。
- [x] 6.2 在 `IOSClient` 中从产品包根目录解析内置 iOS 工具，不能依赖用户 PATH。
- [x] 6.3 修改 `src/perfengine/main.py`，创建 Android backend 和 iOS backend。
- [x] 6.4 在 `main.py` 中注册 `Platform.ANDROID` 和 `Platform.IOS` 到平台注册表。
- [x] 6.5 用平台注册表创建 `PerfToolService`，保持 bridge API 名称不变。
- [x] 6.6 增加后端集成测试或扩展现有服务测试，确认 Android 路径不回归、iOS backend 可被分发调用。
- [x] 6.7 运行 `python -m pytest tests/app tests/android tests/ios -q`，确认后端测试通过。
  - 已执行通过：`python -m pytest tests/app tests/android tests/ios -q --basetemp=.pytest-tmp`，`41 passed in 0.11s`。

## 7. 桌面 UI 平台字段与状态提示

- [x] 7.1 修改 `ui/src/types.ts`，新增 `Platform = 'android' | 'ios'`。
- [x] 7.2 为前端 `DeviceInfo`、`AppInfo`、`SessionState`、`PhoneStatus` 增加平台字段。
- [x] 7.3 为前端 `PhoneStatus` 增加 `status_notice` 字段。
- [x] 7.4 修改 `ui/src/state/sessionStore.ts`，当 snapshot 中有 `status_notice` 时显示状态提示。
- [x] 7.5 修改 `sessionStore`，确保 interrupted/error 仍会停止轮询，running 且仅部分指标缺失时不停止轮询。
- [x] 7.6 修改 `ui/src/components/ToolbarPanel.vue`，在设备选择项中展示平台，例如 `[ios]`、`[android]`。
- [x] 7.7 修改 `ui/src/components/StatusCard.vue`，优先展示 `errorMessage`、`status_notice`、`session.message`、`session.phase`。
- [x] 7.8 修改 `ui/src/components/MetricChart.vue` 或确认其现有行为，确保 `null` 指标显示为空点或断线，不显示为 `0`。
- [x] 7.9 更新 `ui/src/state/sessionStore.spec.ts`，覆盖 iOS 部分指标不可用但 session 继续 running 的状态提示。
- [x] 7.10 更新 `ui/src/components/ToolbarPanel.spec.ts`，覆盖 Android/iOS 设备展示和 selector 锁定。
- [x] 7.11 运行 `npm.cmd test -- --run`，确认 UI 测试通过。
  - 已由用户在本地执行通过：`2 passed` test files，`4 passed` tests。

## 8. 手动验收清单

- [x] 8.1 新建 `docs/manual-tests/ios-mvp-support.md`，写明 Windows + 可信 iPhone 的手动验收环境。
- [x] 8.2 在手动验收清单中加入“不依赖用户已安装 go-ios、sib、pymobiledevice CLI”的检查项。
- [x] 8.3 在手动验收清单中加入设备刷新、选择 iPhone、App 列表、启动采集、图表/状态、停止采集的主流程。
- [x] 8.4 在手动验收清单中加入异常流程：断开 iPhone、退出目标 App、重试采集。
- [x] 8.5 在手动验收清单中加入指标观察记录：FPS、Frame Time、App CPU、Total CPU、Memory、Temperature。
- [x] 8.6 在手动验收清单中说明真机测试由用户执行，开发侧负责根据反馈记录结果和修复问题。

## 9. 最终验证与 OpenSpec 状态

- [x] 9.1 运行 `python -m pytest tests -q`，确认 Python 测试通过。
  - 已执行通过：`python -m pytest tests -q --basetemp=.pytest-tmp`，`43 passed in 0.11s`。
- [x] 9.2 运行 `npm.cmd test -- --run`，确认前端测试通过。
  - 已由用户在本地执行通过：`2 passed` test files，`4 passed` tests。
- [ ] 9.3 运行 `npm.cmd run build`，确认前端生产构建通过。
  - 阻塞：沙箱内执行 Vite build 时 `esbuild` 子进程 `spawn EPERM`。
- [x] 9.4 运行 `openspec.cmd status --change add-ios-mvp-support`，确认 OpenSpec artifacts 仍完整。
  - 已执行通过：`Progress: 4/4 artifacts complete`。
- [x] 9.5 根据用户真机测试反馈，记录 iOS 指标口径差异，重点是 memory、frame time、temperature。
  - 已记录当前真机反馈：设备发现可用；App 列表可用；Start 可进入 running；真实 FPS/system/memory 采集未打通；`sib ps` 和 `sib perfmon` 当前因 `InvalidService` 失败；`sib mount` 当前下载 Developer Disk Image 失败；`sib battery` 可返回电池数据但温度单位仍需确认。
- [ ] 9.6 所有实现和验证完成后，再勾选当前 OpenSpec change 中对应任务。

## 10. 真机反馈后的后续修正

- [ ] 10.1 明确并实现 Developer Disk Image/DDI 准备方案，解决 `sib mount` 下载失败导致的 `InvalidService` 问题。
- [ ] 10.2 接入真实 App 运行状态检测，确保目标 App 退出后 Session Status 能从 running/intermediate 状态切换为明确中断状态。
- [ ] 10.3 接入真实 FPS 和 frame time 数据源，优先使用 `sib perfmon` 或 Demo 中已验证的 DVT/Instruments 路径。
- [ ] 10.4 接入真实 App CPU、Total CPU、Memory 数据源，并确认 Memory 使用 `physFootprint` 口径。
- [ ] 10.5 接入可用的 battery 数据读取；在温度单位确认前继续将 Temperature 保持为空或 unknown。
- [ ] 10.6 修复完成后，由用户再次执行真机主流程和异常流程验证，并把结果写回 `docs/manual-tests/ios-mvp-support.md`。

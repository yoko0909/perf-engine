## 1. 项目骨架与基础模型

- [x] 1.1 创建 `pyproject.toml`，声明 Python 运行依赖和 `pytest` 开发依赖。
- [x] 1.2 创建 `src/perfengine/__init__.py`、`src/perfengine/app/__init__.py`、`src/perfengine/android/__init__.py`、`src/perfengine/ui/__init__.py`。
- [x] 1.3 在 `src/perfengine/app/models.py` 中定义 `DeviceInfo`、`AppInfo`、`SessionPhase`、`SessionState`、`PhoneStatus`、`MetricPoint`、`LiveSnapshot`。
- [x] 1.4 在 `src/perfengine/app/errors.py` 中定义 `OperatorError`，用于承载 QA 可读错误信息。
- [x] 1.5 新建 `tests/app/test_models.py`，验证基础模型默认行为和 `OperatorError` 的消息保真。
- [x] 1.6 运行 `python -m pytest tests/app/test_models.py -q`，确认基础模型测试通过。

## 2. 单会话服务层

- [x] 2.1 新建 `src/perfengine/app/service.py`，建立 `PerfToolService` 单会话服务入口。
- [x] 2.2 在服务层实现 `list_devices()`，覆盖空闲态下的设备刷新流程。
- [x] 2.3 在服务层实现 `list_apps(device_id)`，覆盖设备选中后的应用加载流程。
- [x] 2.4 在服务层实现 `start_session(device_id, package_name)`，覆盖启动中、运行中和启动失败状态。
- [x] 2.5 在服务层实现 `stop_session()`，覆盖停止后恢复选择控件的状态流转。
- [x] 2.6 在 `tests/app/test_service.py` 中验证单会话状态机、选择器锁定和启动失败恢复。
- [x] 2.7 运行 `python -m pytest tests/app/test_service.py -q`，确认服务层状态机测试通过。

## 3. ADB 访问与 Android Provider

- [x] 3.1 新建 `src/perfengine/android/adb_client.py`，统一封装 ADB 命令执行和错误转换。
- [x] 3.2 新建 `src/perfengine/android/device_provider.py`，解析 `adb devices -l` 输出为 `DeviceInfo`。
- [x] 3.3 新建 `src/perfengine/android/app_provider.py`，获取单设备应用列表并映射为 `AppInfo`。
- [x] 3.4 新建 `src/perfengine/android/status_provider.py`，获取连接状态、屏幕状态、应用状态、电量、温度和更新时间。
- [x] 3.5 在 `tests/android/test_providers.py` 中覆盖设备列表解析、应用列表解析和屏幕状态降级为 `unknown` 的情况。
- [x] 3.6 运行 `python -m pytest tests/android/test_providers.py -q`，确认 Android provider 测试通过。

## 4. 指标采样与统一快照

- [x] 4.1 新建 `src/perfengine/android/metrics.py`，把 CPU、内存、Frame Time、FPS 等文本输出归一化为 `MetricPoint`。
- [x] 4.2 新建 `src/perfengine/android/sampler.py`，把指标采样和手机状态整合为单次采样结果。
- [x] 4.3 在服务层 `get_live_snapshot()` 中接入采样器，返回统一的 `LiveSnapshot`。
- [x] 4.4 为 `LiveSnapshot` 增加固定长度历史缓存，支持固定图表滚动显示。
- [x] 4.5 在 `tests/android/test_sampler.py` 中验证指标解析和快照历史追加逻辑。
- [x] 4.6 运行 `python -m pytest tests/android/test_sampler.py -q`，确认快照与采样测试通过。

## 5. 桌面桥接与程序入口

- [x] 5.1 新建 `src/perfengine/ui/bridge.py`，把服务层 dataclass 结果序列化为 pywebview 可直接返回的字典。
- [x] 5.2 新建 `src/perfengine/ui/window.py`，创建桌面窗口并绑定前端入口页面。
- [x] 5.3 新建 `src/perfengine/main.py`，组装 `AdbClient`、provider、sampler、service 和 `BridgeApi`。
- [x] 5.4 在 `tests/ui/test_bridge.py` 中验证桥接层输出的 JSON-ready 数据结构。
- [x] 5.5 运行 `python -m pytest tests/ui/test_bridge.py -q`，确认桌面桥接测试通过。

## 6. 前端工程与轮询状态管理

- [x] 6.1 创建 `ui/package.json`、`ui/tsconfig.json`、`ui/vite.config.ts`、`ui/index.html`、`ui/src/main.ts`。
- [x] 6.2 在 `ui/src/types.ts` 中定义与后端一致的 `DeviceInfo`、`AppInfo`、`SessionState`、`PhoneStatus`、`MetricPoint`、`LiveSnapshot` 类型。
- [x] 6.3 在 `ui/src/api.ts` 中封装 `window.pywebview.api` 调用。
- [x] 6.4 在 `ui/src/state/sessionStore.ts` 中实现设备刷新、应用加载、会话启动、会话停止和每秒一次的快照轮询。
- [x] 6.5 在 `ui/src/state/sessionStore.spec.ts` 中验证启动会话后选择器锁定和前端状态更新。
- [x] 6.6 运行 `npm --prefix ui install`，安装前端依赖。
- [x] 6.7 运行 `npm --prefix ui run test -- sessionStore.spec.ts`，确认前端 store 测试通过。

## 7. 单页仪表盘界面

- [x] 7.1 新建 `ui/src/components/ToolbarPanel.vue`，实现刷新设备、设备选择、应用选择、开始采集、停止采集操作区。
- [x] 7.2 新建 `ui/src/components/StatusCard.vue`，展示连接状态、设备信息、屏幕状态、应用状态、电量、温度和最近刷新时间。
- [x] 7.3 新建 `ui/src/components/MetricChart.vue`，渲染固定图表组件。
- [x] 7.4 新建 `ui/src/App.vue`，在单页中组合顶部操作区、状态卡和固定图表区。
- [x] 7.5 在 `ui/src/components/ToolbarPanel.spec.ts` 中验证运行态下设备和应用选择框被禁用，并显示“停止采集”按钮。
- [x] 7.6 运行 `npm --prefix ui run test -- ToolbarPanel.spec.ts`，确认组件测试通过。
- [x] 7.7 运行 `npm --prefix ui run build`，确认前端静态资源可成功构建。

## 8. 失败状态与恢复体验

- [x] 8.1 在服务层补充“未检测到 Android 设备”的空设备提示。
- [x] 8.2 在服务层补充“等待设备数据中”的无样本提示。
- [x] 8.3 在服务层补充“设备已断开”和“目标应用已退出”的中断提示。
- [x] 8.4 在前端 `sessionStore` 中处理 `error` 和 `interrupted` 状态，停止轮询并保留最后一屏快照。
- [x] 8.5 在 `tests/app/test_error_states.py` 中覆盖空设备、无数据、断连和应用退出场景。
- [x] 8.6 运行 `python -m pytest tests/app/test_error_states.py -q`，确认失败场景测试通过。

## 9. 验证与交付准备

- [x] 9.1 运行 `python -m pytest tests -q`，确认后端测试全集通过。
- [x] 9.2 运行 `npm --prefix ui run test`，确认前端测试全集通过。
- [x] 9.3 新建 `docs/manual-tests/android-qa-perf-desktop-mvp.md`，记录真机验收步骤。
- [x] 9.4 按手工清单验证无设备、选设备、选应用、开始、停止、拔线、应用退出、锁屏场景。
- [x] 9.5 汇总已知限制：单设备、单应用、单会话、无导出、无历史会话、无多平台支持。

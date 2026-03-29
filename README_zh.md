[README](README_zh.md)

# Markdown Alchemy

**万物皆可 Markdown，优雅从未缺席。**

Markdown Alchemy 是一款基于 **PySide6** 和 **QFluentWidgets** 构建的桌面 GUI，为微软 [MarkItDown](https://github.com/microsoft/markitdown) 提供可视化操作界面。拖入文件、粘贴网址，即可获得干净、结构化的 Markdown —— 无需打开终端。

<img width="1660" height="1088" alt="image" src="https://github.com/user-attachments/assets/d412599f-343c-4f87-8408-57ce27ef325d" />
<img width="1667" height="1096" alt="image" src="https://github.com/user-attachments/assets/a811277a-9594-4bdb-9656-9c7e674a7e7d" />
<img width="1669" height="1093" alt="image" src="https://github.com/user-attachments/assets/fa5f1d53-da30-453f-a092-3261fd09cb3c" />

## 为什么选择 Markdown Alchemy？

大多数转换工具只给你一个命令行，剩下的全靠自己。Markdown Alchemy 则为你提供一套现代 Fluent 风格界面 —— 拖放式队列管理、实时进度跟踪、即时预览与批量导出，让你在一次会话中完成数十份文档的转换，全程无需切换窗口。

## 分支归属

**Markdown Alchemy**（[仓库地址](https://github.com/Ayrnio/MarkdownAlchemy)）是 [Jonas / imadreamerboy](https://github.com/imadreamerboy) 所作 **[markitdown-gui](https://github.com/imadreamerboy/markitdown-gui)** 的一个 **fork**。上游项目奠定了坚实的基础；本分支在其之上持续维护，提供更深入的用户体验打磨、更丰富的主题选项以及更多的转换能力。

## 本分支的新增内容

- **实时进度仪表盘** —— 已用时间、文档计数及单文档页码计数器同步实时更新。
- **Perfect Dark 主题** —— 精心调校的深色配色方案，配合定制化的导航栏与标题栏样式、超宽屏幕上自动居中的内容列，以及各处布局细节的润色。
- **兼容 OpenAI 接口的视觉 OCR** —— 将应用指向任意 OpenAI 风格的视觉端点（如 **LM Studio**），即可处理栅格化的 PDF 页面和图片。在设置中直接配置 Base URL、模型和提示词。另有可选的 **"始终 OCR PDF"** 开关，可跳过嵌入文本，专为难以提取的扫描件而设。上游的 Azure 和 Tesseract 流程仍然可用。
- **真正能中断的取消操作** —— 在适用场景下彻底终止进行中的 HTTP 请求，同时为 PDF 解析和模型调用提供更清晰的进度反馈。
- **添加文件夹** —— 从目录中导入顶层文件（不递归子文件夹），并遵守队列视图中的文件类型筛选条件。
- **扩展国际化支持** —— 英文和中文（zh_CN）字符串已覆盖所有新增 UI 元素。

以下上游功能除非另有说明，均继续保留。

## 功能特性

### 转换与工作流
- 基于队列的文件处理流程，支持拖放操作。
- 粘贴 `http://` 或 `https://` 网址，通过托管的 [Defuddle](https://defuddle.md/) API 将网页文章转换为 Markdown。
- 批量转换支持启动、暂停/恢复、取消，并提供细粒度的进度反馈。

### 预览与导出
- 结果视图支持逐文件选择与实时 Markdown 预览。
- 在**渲染视图**和**原始 Markdown 视图**之间自由切换。
- 导出为单个合并文件或多个独立文件。
- 快捷操作：复制 Markdown、保存输出、返回队列或重新开始。

### OCR
- 可选 OCR，支持扫描版 PDF 和图片 —— **Azure 文档智能**、**本地 Tesseract** 或**兼容 OpenAI 的视觉接口**（本分支新增）。

### 设置与个性化
- 输出文件夹、批处理大小、标题样式、表格样式、OCR 引擎、主题模式（**浅色 / 深色 / 跟随系统 / Perfect Dark**）。
- 内置快捷键对话框、检查更新操作及关于对话框。

## 快速开始

### 预构建安装包

前往 [**Releases**](https://github.com/Ayrnio/MarkdownAlchemy/releases) 页面下载最新安装包。原版 **markitdown-gui** 也提供其自身的 [Releases](https://github.com/imadreamerboy/markitdown-gui/releases)（未修改版本）。

### 从源码运行

**前置条件：** Python `3.10+` 以及 [`uv`](https://github.com/astral-sh/uv)（推荐）。

```sh
uv sync
uv run python -m markitdowngui.main
```

或使用 pip：

```sh
pip install -e .[dev]
python -m markitdowngui.main
```

## OCR 配置

OCR 功能**默认关闭**，属于**可选项**。

- **Tesseract（本地）：** 从 [Tesseract 官方项目](https://github.com/tesseract-ocr/tesseract)安装二进制文件。若未加入系统 `PATH`，请在设置中指定可执行文件路径。
- **Azure 文档智能：** 在设置中输入端点地址。如需使用 API 密钥认证，请设置 `AZURE_OCR_API_KEY` 环境变量；否则应用将回退至 `DefaultAzureCredential`。撰写本文时，Azure 提供每月 [500 页免费额度](https://azure.microsoft.com/en-us/products/ai-foundry/tools/document-intelligence#Pricing)。
- **兼容 OpenAI 的视觉接口（如 LM Studio）：** 在设置中配置 Base URL、模型和提示词，具体说明请参阅应用内文档。你需要自行对所指向的服务负责。

## 网页 URL 转换

- 应用将粘贴的 URL 发送至 `https://defuddle.md/<url>`，并将返回的 Markdown 存储到常规结果视图中。
- 响应中通常包含 YAML frontmatter 元数据（如可用）。
- 根据 [Defuddle 服务条款](https://defuddle.md/terms)，未认证请求限制为**每 IP 每月 1,000 次**（截至 2026 年 3 月 14 日）。由于请求直接从桌面应用发出，此限制适用于你的网络 IP。
- 需要有效的网络连接，并依赖 Defuddle 服务的可用性。

## 键盘快捷键

| 快捷键 | 操作 |
|----------|--------|
| `Ctrl+O` | 打开文件 |
| `Ctrl+S` | 保存输出 |
| `Ctrl+C` | 复制输出 |
| `Ctrl+P` | 暂停 / 恢复 |
| `Ctrl+B` | 开始转换 |
| `Ctrl+L` | 清空队列 |
| `Ctrl+K` | 显示快捷键 |
| `Esc` | 取消转换 |

## 构建独立可执行文件

```sh
uv pip install -e .[dev]
pyinstaller MarkItDown.spec --clean --noconfirm
```

默认 spec 文件会在 `dist/` 目录下生成 `onedir` 模式的应用。如需将输出文件夹或可执行文件重命名为 **Markdown Alchemy**，请编辑 `MarkItDown.spec`。

## 参与贡献

1. **Fork** 本仓库（如果你的改动属于上游功能，也可以 fork 上游仓库），然后创建分支。
2. 安装开发依赖：`uv pip install -e .[dev]`
3. 进行修改。
4. 运行测试：`uv run pytest -q`
5. 提交 Pull Request 并附上清晰的说明 —— 如适用，请注明同一修复是否应同步提交到**上游** [markitdown-gui](https://github.com/imadreamerboy/markitdown-gui)。

## 许可协议

基于 **GPLv3 协议授权，仅限非商业用途**。商业使用需获取单独的商业许可证，以遵循 `PySide6-Fluent-Widgets`（`qfluentwidgets`）的非商业授权要求。

## 致谢

- **[markitdown-gui](https://github.com/imadreamerboy/markitdown-gui)** —— MarkItDown 的原始 PySide6 / QFluentWidgets GUI 封装，也是本分支的起点。
- **[MarkItDown](https://github.com/microsoft/markitdown)** — [MIT 许可证](https://opensource.org/licenses/MIT)
- **[PySide6](https://www.qt.io/qt-for-python)** — [LGPLv3 许可证](https://www.gnu.org/licenses/lgpl-3.0.html)
- **[PySide6-Fluent-Widgets / QFluentWidgets](https://qfluentwidgets.com/)**
- 导航切换图标源自 **Lucide** 的 [infinity](https://lucide.dev/icons/infinity) 图标 — [ISC 许可证](https://lucide.dev/license)
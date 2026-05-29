# 存储桶浏览器 (OSScheak)

一个用于浏览和预览云存储桶内容的桌面应用程序。

## 功能特性

- 📁 **多存储桶支持**: 支持 MinIO、阿里云OSS、华为云OBS、腾讯云COS、Google Cloud Storage、Azure Blob Storage
- 🖼️ **内容预览**: 支持图片、PDF、DOC/DOCX、XLS/XLSX、PPT/PPTX等文件的内容预览
- 🔍 **文件搜索**: 支持按文件名搜索过滤
- 🖱️ **右键菜单**: 支持复制URL、在浏览器中打开、查看文件信息
- 🖼️ **双击放大**: 双击缩略图可放大查看详细内容
- ⚡ **性能优化**: 异步加载、LRU缓存、预加载机制

## 技术栈

- Python 3.8+
- Tkinter (GUI框架)
- Pillow (图片处理)
- Requests (HTTP请求)
- PyMuPDF (PDF解析)
- python-docx (DOCX解析)
- openpyxl (XLSX解析)
- python-pptx (PPTX解析)
- xlrd (XLS解析)

## 项目结构

```
OSScheak/
├── src/                    # 源代码目录
│   ├── __init__.py         # 包初始化
│   ├── config.py           # 配置模块
│   ├── bucket_parser.py    # 存储桶响应解析器
│   ├── document_processor.py # 文档处理器
│   ├── http_client.py      # HTTP客户端
│   ├── cache_manager.py    # 缓存管理器
│   └── gui/                # GUI模块
│       └── main_window.py  # 主窗口
├── main.py                 # 主入口文件
├── OssCheak.vbs            # VBS启动脚本
└── README.md               # 项目说明
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 快速开始

### 方法1: 使用VBS脚本启动

双击 `OssCheak.vbs` 文件即可启动应用。

### 方法2: 使用命令行启动

```bash
python main.py
```

## 使用说明

1. **输入存储桶URL**: 在顶部输入框中输入存储桶的URL地址
2. **加载内容**: 点击"加载内容"按钮获取存储桶中的文件列表
3. **浏览文件**: 使用滚动条浏览文件缩略图
4. **搜索文件**: 在搜索框中输入关键词过滤文件
5. **预览文件**: 双击文件缩略图放大查看内容
6. **右键操作**: 右键点击文件可复制URL或在浏览器中打开

## 支持的存储桶类型

| 存储类型 | URL示例 |
|---------|--------|
| MinIO | `https://your-minio-server/minio/bucket/` |
| 阿里云OSS | `https://your-bucket.oss-cn-region.aliyuncs.com/` |
| 华为云OBS | `https://your-bucket.obs-region.myhuaweicloud.com/` |
| 腾讯云COS | `https://your-bucket.cos.region.myqcloud.com/` |
| Google Cloud Storage | `https://storage.googleapis.com/your-bucket/` |
| Azure Blob Storage | `https://your-account.blob.core.windows.net/your-container/` |

## 支持的文件预览类型

- **图片**: PNG, JPG, JPEG, GIF, BMP
- **文档**: PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX
- **文本**: TXT, JSON, XML, CSV, HTML

## 性能优化策略

1. **异步加载**: 网络请求在后台线程执行，不阻塞UI
2. **LRU缓存**: 缩略图和预览内容使用LRU缓存，避免重复请求
3. **预加载**: 自动预加载前几个文件的内容
4. **懒加载**: 只加载可见区域的缩略图

## 配置说明

配置文件位于 `src/config.py`，可调整以下参数：

- `THUMBNAIL_SIZE`: 缩略图尺寸 (默认: 120x120)
- `CACHE_MAX_SIZE`: 缓存最大条目数 (默认: 50)
- `PRELOAD_COUNT`: 预加载文件数量 (默认: 3)
- `REQUEST_TIMEOUT`: 请求超时时间 (默认: 30秒)

## 开发说明

### 添加新的存储桶类型

在 `src/bucket_parser.py` 中添加新的解析方法，并在 `detect_bucket_type` 方法中添加类型检测逻辑。

### 添加新的文件类型支持

在 `src/document_processor.py` 中添加对应的内容提取和缩略图生成方法。

## 许可证

MIT License

## 作者

OSScheak Team

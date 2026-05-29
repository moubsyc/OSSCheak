"""配置模块 - 包含项目常量和配置设置"""

# 性能优化常量
PREVIEW_SIZE_LIMIT = 10240  # 10KB - 文本文件预览大小限制
THUMBNAIL_SIZE = (120, 120)  # 缩略图尺寸
CACHE_MAX_SIZE = 50  # LRU缓存最大条目数
PRELOAD_COUNT = 3  # 预加载文件数量

# 需要预加载的文件类型
PRELOAD_TYPES = {
    'PDF', 'DOCX', 'XLSX', 'PPTX', 'DOC', 'XLS',
    'PNG', 'JPG', 'JPEG', 'GIF', 'BMP',
    'TXT', 'JSON', 'XML', 'CSV'
}

# 图片文件类型
IMAGE_TYPES = {'PNG', 'JPG', 'JPEG', 'GIF', 'BMP'}

# 文档文件类型
DOC_TYPES = {'PDF', 'DOCX', 'XLSX', 'PPTX', 'DOC', 'XLS', 'CSV'}

# 文本文件类型
TEXT_TYPES = {'TXT', 'JSON', 'XML', 'CSV', 'HTML', 'MD'}

# 存储桶类型映射
BUCKET_TYPES = {
    'minio': 'MinIO',
    'oss': '阿里云OSS',
    'obs': '华为云OBS',
    'cos': '腾讯云COS',
    'gcs': 'Google Cloud Storage',
    'azure': 'Azure Blob Storage',
    's3': 'Amazon S3'
}

# 请求配置
REQUEST_TIMEOUT = 30
REQUEST_RETRIES = 3
REQUEST_DELAY = 1  # 重试延迟（秒）

# UI配置
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 700
ZOOM_WINDOW_WIDTH = 800
ZOOM_WINDOW_HEIGHT = 600

# 缩略图配置
THUMBNAIL_PADDING = 5
THUMBNAIL_SPACING = 10

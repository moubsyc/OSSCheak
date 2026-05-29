"""缓存管理模块 - 管理缩略图和预览内容的缓存"""

from collections import OrderedDict


class CacheManager:
    """LRU缓存管理器"""
    
    def __init__(self, max_size=50):
        self.max_size = max_size
        self.cache = OrderedDict()
    
    def get(self, key):
        """获取缓存项"""
        if key in self.cache:
            # 移动到末尾表示最近使用
            self.cache.move_to_end(key)
            return self.cache[key]
        return None
    
    def set(self, key, value):
        """设置缓存项"""
        if key in self.cache:
            self.cache.move_to_end(key)
        else:
            # 如果缓存已满，删除最旧的项
            while len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)
        
        self.cache[key] = value
    
    def has(self, key):
        """检查缓存是否存在"""
        return key in self.cache
    
    def remove(self, key):
        """删除缓存项"""
        if key in self.cache:
            del self.cache[key]
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
    
    def size(self):
        """获取缓存大小"""
        return len(self.cache)
    
    def keys(self):
        """获取所有缓存键"""
        return list(self.cache.keys())


class ThumbnailCache(CacheManager):
    """缩略图缓存"""
    
    def __init__(self, max_size=50):
        super().__init__(max_size)
    
    def get_thumbnail(self, url):
        """获取缩略图"""
        return self.get(url)
    
    def set_thumbnail(self, url, photo):
        """设置缩略图"""
        self.set(url, photo)


class PreviewCache(CacheManager):
    """预览内容缓存"""
    
    def __init__(self, max_size=20):
        super().__init__(max_size)
    
    def get_preview(self, url):
        """获取预览内容"""
        return self.get(url)
    
    def set_preview(self, url, content):
        """设置预览内容"""
        self.set(url, content)

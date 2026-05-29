"""HTTP客户端模块 - 处理网络请求和会话管理"""

import requests
import time
from urllib.parse import urlparse


class HttpClient:
    """HTTP客户端 - 封装网络请求逻辑"""
    
    def __init__(self, timeout=10, retries=2, delay=0.5):
        self.timeout = timeout
        self.retries = retries
        self.delay = delay
        self.session = self._create_session()
    
    def _create_session(self):
        """创建会话对象"""
        session = requests.Session()
        
        # 设置默认请求头（模拟浏览器）
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0'
        })
        
        # 设置连接池大小
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10,
            max_retries=self.retries
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        return session
    
    def get(self, url, **kwargs):
        """发送GET请求（带重试机制）"""
        # 如果kwargs中没有timeout，使用默认值
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.timeout
        
        for attempt in range(self.retries):
            try:
                response = self.session.get(url, **kwargs)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                if attempt < self.retries - 1:
                    time.sleep(self.delay * (attempt + 1))
                    continue
                raise e
    
    def head(self, url, **kwargs):
        """发送HEAD请求"""
        for attempt in range(self.retries):
            try:
                response = self.session.head(url, timeout=self.timeout, **kwargs)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                if attempt < self.retries - 1:
                    time.sleep(self.delay * (attempt + 1))
                    continue
                raise e
    
    def download_file(self, url, chunk_size=1024*1024):
        """流式下载文件"""
        response = self.get(url, stream=True)
        
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                yield chunk
    
    def get_content_type(self, url):
        """获取URL的Content-Type"""
        try:
            response = self.head(url)
            return response.headers.get('Content-Type', '')
        except Exception:
            return ''
    
    def is_accessible(self, url):
        """检查URL是否可访问"""
        try:
            response = self.head(url, timeout=10)
            return response.status_code == 200
        except Exception:
            return False
    
    def close(self):
        """关闭会话"""
        self.session.close()

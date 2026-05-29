"""存储桶解析器模块 - 解析不同类型存储桶的响应"""

import re
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse


class BucketParser:
    """存储桶响应解析器"""
    
    @staticmethod
    def detect_bucket_type(url):
        """检测存储桶类型"""
        parsed = urlparse(url)
        hostname = parsed.hostname.lower()
        
        if 'minio' in hostname:
            return 'minio'
        elif 'oss-' in hostname and 'aliyuncs.com' in hostname:
            return 'oss'
        elif 'obs-' in hostname and 'huaweicloud.com' in hostname:
            return 'obs'
        elif 'cos.' in hostname and 'myqcloud.com' in hostname:
            return 'cos'
        elif 'storage.googleapis.com' in hostname:
            return 'gcs'
        elif 'blob.core.windows.net' in hostname:
            return 'azure'
        elif 's3.' in hostname or 'amazonaws.com' in hostname:
            return 's3'
        else:
            # 默认尝试多种解析方式
            return 'unknown'
    
    @staticmethod
    def parse_minio_response(bucket_url, content):
        """解析MinIO响应（HTML格式）"""
        files = []
        
        try:
            # 提取<tr>行中的文件信息
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', content, re.DOTALL)
            for row in rows:
                # 查找链接
                link_match = re.search(r'<a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>', row)
                if link_match:
                    href = link_match.group(1)
                    name = link_match.group(2).strip()
                    
                    # 跳过目录链接和表头
                    if name in ['Name', '..', '/']:
                        continue
                    
                    # 获取文件大小
                    size_match = re.search(r'<td[^>]*>([\d.,]+)\s*(KB|MB|GB|Bytes?)?</td>', row)
                    file_size = size_match.group(0).strip() if size_match else '未知'
                    
                    # 构建完整URL
                    file_url = urljoin(bucket_url, href)
                    
                    # 确定文件类型
                    file_type = BucketParser._get_file_type(name)
                    
                    files.append({
                        'name': name,
                        'url': file_url,
                        'size': file_size,
                        'type': file_type,
                        'is_folder': name.endswith('/')
                    })
        except Exception:
            pass
        
        return files
    
    @staticmethod
    def parse_minio_xml(bucket_url, content):
        """解析MinIO的XML响应（S3兼容格式）"""
        files = []
        
        try:
            root = ET.fromstring(content)
            
            # MinIO使用S3格式，带有命名空间
            namespaces = [
                'http://s3.amazonaws.com/doc/2006-03-01/',
                'http://doc.s3.amazonaws.com/2006-03-01'
            ]
            
            # 尝试带命名空间的解析
            for ns in namespaces:
                contents = root.findall('.//{' + ns + '}Contents')
                if contents:
                    for item in contents:
                        key_elem = item.find('{' + ns + '}Key')
                        size_elem = item.find('{' + ns + '}Size')
                        
                        if key_elem is not None and key_elem.text:
                            name = key_elem.text
                            if not name.endswith('/'):
                                file_url = urljoin(bucket_url, name)
                                file_size = size_elem.text if size_elem is not None else '未知'
                                file_size = BucketParser._format_size(file_size)
                                
                                files.append({
                                    'name': os.path.basename(name),
                                    'url': file_url,
                                    'size': file_size,
                                    'type': BucketParser._get_file_type(name),
                                    'is_folder': False
                                })
                    return files
            
            # 尝试不带命名空间的解析
            contents = root.findall('.//Contents')
            for item in contents:
                key_elem = item.find('Key')
                size_elem = item.find('Size')
                
                if key_elem is not None and key_elem.text:
                    name = key_elem.text
                    if not name.endswith('/'):
                        file_url = urljoin(bucket_url, name)
                        file_size = size_elem.text if size_elem is not None else '未知'
                        file_size = BucketParser._format_size(file_size)
                        
                        files.append({
                            'name': os.path.basename(name),
                            'url': file_url,
                            'size': file_size,
                            'type': BucketParser._get_file_type(name),
                            'is_folder': False
                        })
        except Exception:
            pass
        
        return files
    
    @staticmethod
    def parse_oss_xml(bucket_url, content):
        """解析阿里云OSS响应（XML格式）"""
        files = []
        
        try:
            root = ET.fromstring(content)
            
            # 尝试多种命名空间
            ns_map = {
                '': 'http://doc.s3.amazonaws.com/2006-03-01',
                'ns': 'http://doc.s3.amazonaws.com/2006-03-01',
                'o': 'http://oss.aliyuncs.com/doc/2011-06-15/'
            }
            
            # 查找Contents节点
            contents = []
            for ns in ns_map.values():
                contents.extend(root.findall('.//{' + ns + '}Contents'))
            
            if not contents:
                # 没有命名空间的情况
                contents = root.findall('.//Contents')
            
            for item in contents:
                key_elem = item.find('Key') or item.find('.//Key')
                size_elem = item.find('Size') or item.find('.//Size')
                
                if key_elem is not None:
                    name = key_elem.text
                    if name and not name.endswith('/'):
                        file_url = urljoin(bucket_url, name)
                        file_size = size_elem.text if size_elem is not None else '未知'
                        file_size = BucketParser._format_size(file_size)
                        
                        files.append({
                            'name': os.path.basename(name),
                            'url': file_url,
                            'size': file_size,
                            'type': BucketParser._get_file_type(name),
                            'is_folder': False
                        })
        except Exception:
            pass
        
        return files
    
    @staticmethod
    def parse_obs_xml(bucket_url, content):
        """解析华为云OBS响应（XML格式）"""
        files = []
        
        try:
            root = ET.fromstring(content)
            
            # 查找Contents节点（华为云OBS格式）
            contents = root.findall('.//Contents')
            
            for item in contents:
                key_elem = item.find('Key')
                size_elem = item.find('Size')
                
                if key_elem is not None and key_elem.text:
                    name = key_elem.text
                    if not name.endswith('/'):
                        file_url = urljoin(bucket_url, name)
                        file_size = size_elem.text if size_elem is not None else '未知'
                        file_size = BucketParser._format_size(file_size)
                        
                        files.append({
                            'name': os.path.basename(name),
                            'url': file_url,
                            'size': file_size,
                            'type': BucketParser._get_file_type(name),
                            'is_folder': False
                        })
        except Exception:
            pass
        
        return files
    
    @staticmethod
    def parse_cos_xml(bucket_url, content):
        """解析腾讯云COS响应（XML格式）"""
        files = []
        
        try:
            root = ET.fromstring(content)
            
            # 查找Contents节点
            contents = root.findall('.//Contents')
            
            for item in contents:
                key_elem = item.find('Key')
                size_elem = item.find('Size')
                
                if key_elem is not None and key_elem.text:
                    name = key_elem.text
                    if not name.endswith('/'):
                        file_url = urljoin(bucket_url, name)
                        file_size = size_elem.text if size_elem is not None else '未知'
                        file_size = BucketParser._format_size(file_size)
                        
                        files.append({
                            'name': os.path.basename(name),
                            'url': file_url,
                            'size': file_size,
                            'type': BucketParser._get_file_type(name),
                            'is_folder': False
                        })
        except Exception:
            pass
        
        return files
    
    @staticmethod
    def parse_gcs_xml(bucket_url, content):
        """解析Google Cloud Storage响应（XML格式）"""
        files = []
        
        try:
            root = ET.fromstring(content)
            
            # GCS使用Atom格式
            entries = root.findall('.//{http://www.w3.org/2005/Atom}entry')
            
            for entry in entries:
                title_elem = entry.find('{http://www.w3.org/2005/Atom}title')
                link_elem = entry.find('{http://www.w3.org/2005/Atom}link')
                size_elem = entry.find('{http://schemas.google.com/g/2005}size')
                
                if title_elem is not None and title_elem.text:
                    name = title_elem.text
                    if not name.endswith('/'):
                        file_url = link_elem.get('href') if link_elem is not None else urljoin(bucket_url, name)
                        file_size = size_elem.text if size_elem is not None else '未知'
                        file_size = BucketParser._format_size(file_size)
                        
                        files.append({
                            'name': name,
                            'url': file_url,
                            'size': file_size,
                            'type': BucketParser._get_file_type(name),
                            'is_folder': False
                        })
        except Exception:
            pass
        
        return files
    
    @staticmethod
    def parse_azure_xml(bucket_url, content):
        """解析Azure Blob Storage响应（XML格式）"""
        files = []
        
        try:
            root = ET.fromstring(content)
            
            # Azure Blob格式
            blobs = root.findall('.//Blob')
            
            for blob in blobs:
                name_elem = blob.find('Name')
                url_elem = blob.find('Url')
                size_elem = blob.find('Properties/ContentLength')
                
                if name_elem is not None and name_elem.text:
                    name = name_elem.text
                    if not name.endswith('/'):
                        file_url = url_elem.text if url_elem is not None else urljoin(bucket_url, name)
                        file_size = size_elem.text if size_elem is not None else '未知'
                        file_size = BucketParser._format_size(file_size)
                        
                        files.append({
                            'name': name,
                            'url': file_url,
                            'size': file_size,
                            'type': BucketParser._get_file_type(name),
                            'is_folder': False
                        })
        except Exception:
            pass
        
        return files
    
    @staticmethod
    def parse_generic_html(bucket_url, content):
        """通用HTML解析（尝试从任意HTML页面提取链接）"""
        files = []
        
        try:
            # 提取所有链接
            links = re.findall(r'<a[^>]*href="([^"]+)"[^>]*>([^<]*)</a>', content)
            
            for href, text in links:
                # 过滤无效链接
                if href.startswith('http') or href.startswith('/'):
                    if href.startswith('/'):
                        file_url = urljoin(bucket_url, href)
                    else:
                        file_url = href
                    
                    name = text.strip() or os.path.basename(href)
                    
                    # 跳过目录和特殊链接
                    if name and not name in ['..', '/', 'Parent Directory'] and not href.startswith('?'):
                        files.append({
                            'name': name,
                            'url': file_url,
                            'size': '未知',
                            'type': BucketParser._get_file_type(name),
                            'is_folder': name.endswith('/') or href.endswith('/')
                        })
        except Exception:
            pass
        
        return files
    
    @staticmethod
    def parse_response(bucket_url, content, content_type):
        """根据内容类型选择合适的解析器"""
        bucket_type = BucketParser.detect_bucket_type(bucket_url)
        
        # 根据内容类型和存储桶类型选择解析器
        if content_type and 'xml' in content_type.lower():
            if bucket_type == 'minio':
                # MinIO也可能返回XML格式（S3兼容API）
                return BucketParser.parse_minio_xml(bucket_url, content)
            elif bucket_type == 'oss':
                return BucketParser.parse_oss_xml(bucket_url, content)
            elif bucket_type == 'obs':
                return BucketParser.parse_obs_xml(bucket_url, content)
            elif bucket_type == 'cos':
                return BucketParser.parse_cos_xml(bucket_url, content)
            elif bucket_type == 'gcs':
                return BucketParser.parse_gcs_xml(bucket_url, content)
            elif bucket_type == 'azure':
                return BucketParser.parse_azure_xml(bucket_url, content)
            else:
                # 通用XML解析 - 尝试多种方式
                result = BucketParser.parse_minio_xml(bucket_url, content)
                if not result:
                    result = BucketParser.parse_oss_xml(bucket_url, content)
                return result
        elif content_type and 'html' in content_type.lower():
            if bucket_type == 'minio':
                return BucketParser.parse_minio_response(bucket_url, content)
            else:
                return BucketParser.parse_generic_html(bucket_url, content)
        else:
            # 尝试多种解析方式
            result = BucketParser.parse_minio_response(bucket_url, content)
            if not result:
                result = BucketParser.parse_minio_xml(bucket_url, content)
            if not result:
                result = BucketParser.parse_oss_xml(bucket_url, content)
            if not result:
                result = BucketParser.parse_generic_html(bucket_url, content)
            return result
    
    @staticmethod
    def _get_file_type(filename):
        """根据文件名获取文件类型"""
        ext = filename.split('.')[-1].upper() if '.' in filename else 'UNKNOWN'
        
        # 图片类型
        image_exts = {'PNG', 'JPG', 'JPEG', 'GIF', 'BMP', 'WEBP', 'ICO'}
        if ext in image_exts:
            return ext
        
        # 文档类型
        doc_exts = {'PDF', 'DOC', 'DOCX', 'XLS', 'XLSX', 'PPT', 'PPTX'}
        if ext in doc_exts:
            return ext
        
        # 文本类型
        text_exts = {'TXT', 'JSON', 'XML', 'CSV', 'HTML', 'HTM', 'MD', 'LOG'}
        if ext in text_exts:
            return ext
        
        # 压缩类型
        zip_exts = {'ZIP', 'RAR', '7Z', 'GZ', 'TAR'}
        if ext in zip_exts:
            return ext
        
        return 'OTHER'
    
    @staticmethod
    def _format_size(size_str):
        """格式化文件大小"""
        try:
            size = int(size_str)
            if size < 1024:
                return f"{size} Bytes"
            elif size < 1024 * 1024:
                return f"{size / 1024:.2f} KB"
            elif size < 1024 * 1024 * 1024:
                return f"{size / (1024 * 1024):.2f} MB"
            else:
                return f"{size / (1024 * 1024 * 1024):.2f} GB"
        except:
            return str(size_str)


import os  # 需要在模块末尾导入，避免循环依赖

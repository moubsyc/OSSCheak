"""主窗口模块 - 存储桶浏览器的主界面"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from PIL import Image, ImageTk
import threading
import webbrowser
import io
import time

from src.config import (
    THUMBNAIL_SIZE, CACHE_MAX_SIZE,
    IMAGE_TYPES, DOC_TYPES, TEXT_TYPES
)
from src.bucket_parser import BucketParser
from src.document_processor import DocumentProcessor
from src.http_client import HttpClient
from src.cache_manager import ThumbnailCache


class StorageBrowser:
    """存储桶浏览器主类"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("存储桶浏览器")
        self.root.geometry("1200x800")
        
        # 状态变量
        self.current_url = ""
        self.all_files = []  # 保存所有原始文件
        self.current_files = []  # 当前显示的文件（可能被筛选）
        self.is_loading = False
        self.loaded_thumbnails = set()
        self.loading_lock = threading.Lock()
        
        # 初始化组件
        self.http_client = HttpClient(timeout=8, retries=2)
        self.thumbnail_cache = ThumbnailCache(max_size=CACHE_MAX_SIZE)
        self.thumbnail_widgets = []
        
        # 创建UI
        self._create_widgets()
    
    def _create_widgets(self):
        """创建UI组件"""
        # 顶部工具栏
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(toolbar, text="存储桶URL:").pack(side=tk.LEFT, padx=5)
        self.url_entry = ttk.Entry(toolbar, width=80)
        self.url_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.load_btn = ttk.Button(toolbar, text="加载内容", command=self.load_bucket)
        self.load_btn.pack(side=tk.LEFT, padx=5)
        
        self.view_source_btn = ttk.Button(toolbar, text="查看源码", command=self.view_source)
        self.view_source_btn.pack(side=tk.LEFT, padx=5)
        
        # 文件筛选
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)
        
        ttk.Label(toolbar, text="筛选后缀:").pack(side=tk.LEFT, padx=5)
        self.filter_var = tk.StringVar(value="")
        self.filter_combobox = ttk.Combobox(toolbar, textvariable=self.filter_var, width=15, state="readonly")
        self.filter_combobox['values'] = ['全部', '图片', 'XLS/XLSX', 'PDF', 'DOC/DOCX', 'PPT/PPTX', 'TXT', 'CSV', 'HTML']
        self.filter_combobox.pack(side=tk.LEFT, padx=5)
        self.filter_combobox.bind('<<ComboboxSelected>>', self._on_filter_change)
        
        # 文件列表区域
        container = ttk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.container = container  # 保存引用
        
        self.scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.canvas = tk.Canvas(container, yscrollcommand=self.scrollbar.set, bg='#f5f5f5')
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.configure(command=self._on_scroll)
        
        # 使用全局绑定方式，让整个窗口都支持滚轮滚动
        # bind_all 会将事件绑定到所有 widget，无论鼠标在哪个位置都能触发
        self.root.bind_all('<MouseWheel>', self._on_global_mousewheel)
        self.root.bind_all('<Button-4>', self._on_global_mousewheel)
        self.root.bind_all('<Button-5>', self._on_global_mousewheel)
        
        # 使用居中对齐的frame
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # 更新滚动区域
        self.scrollable_frame.bind("<Configure>", self._update_scroll_region)
        
        # 底部状态栏
        self.status_bar = ttk.Label(self.root, text="就绪", relief=tk.SUNKEN)
        self.status_bar.pack(fill=tk.X, padx=10, pady=5)
        
        # 滚动延迟定时器
        self.scroll_timer = None
        
        # 窗口大小变化绑定
        self.root.bind('<Configure>', self._on_main_window_resize)
        
        # 当前列数
        self.current_cols = 6
    
    def _update_scroll_region(self, event):
        """更新滚动区域"""
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
    
    def _on_main_window_resize(self, event):
        """主窗口大小变化时重新布局"""
        if not self.current_files:
            return
        
        # 计算新的列数
        canvas_width = self.canvas.winfo_width()
        item_width = THUMBNAIL_SIZE[0] + 20  # 缩略图宽度 + padding
        
        # 最小4列，最大10列
        new_cols = max(4, min(10, canvas_width // item_width))
        
        # 如果列数变化，重新布局
        if new_cols != self.current_cols and new_cols >= 1:
            self.current_cols = new_cols
            self._rearrange_files()
    
    def _rearrange_files(self):
        """重新排列文件网格（居中对齐）"""
        if not self.current_files:
            return
        
        # 重新排列已有的widget
        cols = self.current_cols
        
        for i, widget in enumerate(self.thumbnail_widgets):
            row = i // cols
            col = i % cols
            widget.grid(row=row, column=col, padx=3, pady=3)
        
        # 更新滚动区域
        self.scrollable_frame.update_idletasks()
        
        # 计算居中偏移
        canvas_width = self.canvas.winfo_width()
        frame_width = self.scrollable_frame.winfo_width()
        
        # 如果frame宽度小于canvas宽度，居中显示
        if frame_width < canvas_width:
            offset_x = (canvas_width - frame_width) // 2
        else:
            offset_x = 0
        
        # 更新canvas窗口位置（居中）
        self.canvas.coords("!window", offset_x, 0)
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
    
    def _on_scroll(self, *args):
        """处理滚动事件"""
        self.canvas.yview(*args)
        
        # 清除之前的定时器
        if self.scroll_timer:
            self.root.after_cancel(self.scroll_timer)
        
        # 滚动停止后100ms加载可见区域的缩略图
        self.scroll_timer = self.root.after(100, self._load_visible_thumbnails)
    
    def _on_global_mousewheel(self, event):
        """全局鼠标滚轮事件处理 - 支持整个窗口范围内的滚轮滚动"""
        # 计算滚动量
        if hasattr(event, 'delta'):
            # Windows/Mac系统：delta值为正负120
            delta = event.delta
        else:
            # Linux系统：Button-4是向上滚动，Button-5是向下滚动
            delta = -1 if event.num == 5 else 1
        
        # 执行滚动
        if delta > 0:
            # 向上滚动
            self.canvas.yview_scroll(-1, 'units')
        else:
            # 向下滚动
            self.canvas.yview_scroll(1, 'units')
        
        # 触发滚动延迟加载
        if self.scroll_timer:
            self.root.after_cancel(self.scroll_timer)
        self.scroll_timer = self.root.after(100, self._load_visible_thumbnails)
    
    def _load_visible_thumbnails(self):
        """加载可见区域的缩略图"""
        if not self.current_files:
            return
        
        # 获取可见区域
        canvas_height = self.canvas.winfo_height()
        y0, y1 = self.canvas.yview()
        
        cols = self.current_cols
        
        # 计算可见范围内的文件索引
        item_height = THUMBNAIL_SIZE[1] + 45  # 缩略图高度 + padding
        visible_start = int(y0 * len(self.current_files) / cols) * cols
        visible_end = min(int(y1 * len(self.current_files) / cols + 3) * cols, len(self.current_files))
        
        # 预加载前后各两行
        load_start = max(0, visible_start - cols * 2)
        load_end = min(len(self.current_files), visible_end + cols * 2)
        
        # 加载可见区域的缩略图
        self._load_thumbnails_in_range(load_start, load_end)
    
    def _load_thumbnails_in_range(self, start, end):
        """加载指定范围的缩略图"""
        for i in range(start, end):
            if i not in self.loaded_thumbnails:
                self._start_thumbnail_load(i, self.current_files[i])
    
    def _start_thumbnail_load(self, idx, file_info):
        """启动单个缩略图加载"""
        with self.loading_lock:
            if idx in self.loaded_thumbnails:
                return
            self.loaded_thumbnails.add(idx)
        
        thread = threading.Thread(target=self._load_file_thumbnail, args=(idx, file_info))
        thread.daemon = True
        thread.start()
    
    def load_bucket(self):
        """加载存储桶内容"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("警告", "请输入存储桶URL")
            return
        
        if self.is_loading:
            return
        
        self.is_loading = True
        self.load_btn.config(state=tk.DISABLED)
        self.status_bar.config(text="正在加载...")
        
        # 重置状态
        self.loaded_thumbnails.clear()
        
        def async_load():
            try:
                self.current_url = url
                self.all_files = self._fetch_bucket_content(url)
                self._apply_filter()  # 应用当前筛选
                self.root.after(0, self._display_files)
            except Exception as e:
                error_msg = str(e)
                self.root.after(0, lambda: self._show_load_error(error_msg))
            finally:
                self.root.after(0, self._finish_loading)
        
        thread = threading.Thread(target=async_load)
        thread.daemon = True
        thread.start()
    
    def _fetch_bucket_content(self, url):
        """获取存储桶内容"""
        if not url.endswith('/'):
            url += '/'
        
        response = self.http_client.get(url)
        return BucketParser.parse_response(url, response.text, response.headers.get('Content-Type', ''))
    
    def _display_files(self):
        """显示文件列表（居中对齐）"""
        # 清空现有内容
        for widget in self.thumbnail_widgets:
            widget.destroy()
        self.thumbnail_widgets.clear()
        
        if not self.current_files:
            self.status_bar.config(text="加载完成，共 0 个文件")
            return
        
        # 计算列数
        canvas_width = self.canvas.winfo_width()
        item_width = THUMBNAIL_SIZE[0] + 6  # 减少padding
        cols = max(4, min(10, canvas_width // item_width))
        self.current_cols = cols if cols >= 1 else 6
        
        # 使用居中对齐的方式显示文件
        # 先计算所有文件的网格大小
        total_items = len(self.current_files)
        rows = (total_items + cols - 1) // cols
        
        for i, file_info in enumerate(self.current_files):
            row = i // cols
            col = i % cols
            
            frame = self._create_file_thumbnail(file_info)
            frame.grid(row=row, column=col, padx=3, pady=3)
            self.thumbnail_widgets.append(frame)
        
        # 状态栏更新由 _apply_filter 处理
        
        # 更新滚动区域并居中
        self.scrollable_frame.update_idletasks()
        
        # 计算居中偏移
        frame_width = self.scrollable_frame.winfo_width()
        if frame_width < canvas_width:
            offset_x = (canvas_width - frame_width) // 2
        else:
            offset_x = 0
        
        # 更新canvas窗口位置（居中）
        self.canvas.coords("!window", offset_x, 0)
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        
        # 立即加载前4行的缩略图
        self._load_thumbnails_in_range(0, min(cols * 4, len(self.current_files)))
    
    def _on_filter_change(self, event=None):
        """筛选条件变化时触发"""
        self._apply_filter()
        # 重置已加载的缩略图
        self.loaded_thumbnails.clear()
        self._display_files()
    
    def _apply_filter(self):
        """应用筛选条件"""
        filter_type = self.filter_var.get()
        
        if not filter_type or filter_type == '全部':
            self.current_files = self.all_files.copy()
        else:
            # 根据筛选类型过滤文件
            filtered_files = []
            for file_info in self.all_files:
                file_type = file_info.get('type', '').upper()
                
                if filter_type == '图片':
                    if file_type in IMAGE_TYPES:
                        filtered_files.append(file_info)
                elif filter_type == '文档':
                    if file_type in DOC_TYPES or file_type in TEXT_TYPES:
                        filtered_files.append(file_info)
                elif filter_type == 'XLS/XLSX':
                    if file_type in ['XLS', 'XLSX']:
                        filtered_files.append(file_info)
                elif filter_type == 'PDF':
                    if file_type == 'PDF':
                        filtered_files.append(file_info)
                elif filter_type == 'DOC/DOCX':
                    if file_type in ['DOC', 'DOCX']:
                        filtered_files.append(file_info)
                elif filter_type == 'PPT/PPTX':
                    if file_type in ['PPT', 'PPTX']:
                        filtered_files.append(file_info)
                elif filter_type == 'TXT':
                    if file_type == 'TXT':
                        filtered_files.append(file_info)
                elif filter_type == 'CSV':
                    if file_type == 'CSV':
                        filtered_files.append(file_info)
                elif filter_type == 'HTML':
                    if file_type in ['HTML', 'HTM']:
                        filtered_files.append(file_info)
            
            self.current_files = filtered_files
        
        # 更新状态栏显示
        total_count = len(self.all_files)
        filtered_count = len(self.current_files)
        if filter_type and filter_type != '全部':
            self.status_bar.config(text=f"筛选结果: {filtered_count}/{total_count} 个文件")
        else:
            self.status_bar.config(text=f"加载完成，共{total_count}个文件")
    
    def _load_file_thumbnail(self, idx, file_info):
        """加载单个文件缩略图"""
        if idx >= len(self.thumbnail_widgets):
            return
        
        frame = self.thumbnail_widgets[idx]
        canvas = frame.winfo_children()[0]
        
        file_type = file_info['type'].upper()
        cache_key = file_info['url']
        
        # 检查缓存
        if self.thumbnail_cache.has(cache_key):
            photo = self.thumbnail_cache.get_thumbnail(cache_key)
            self.root.after(0, lambda: self._update_canvas(canvas, photo))
            return
        
        try:
            if file_type in IMAGE_TYPES:
                response = self.http_client.get(file_info['url'])
                img = Image.open(io.BytesIO(response.content))
                img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
            elif file_type in DOC_TYPES:
                response = self.http_client.get(file_info['url'])
                img = DocumentProcessor.create_thumbnail(file_type, response.content, THUMBNAIL_SIZE)
                photo = ImageTk.PhotoImage(img)
            else:
                return
            
            self.thumbnail_cache.set_thumbnail(cache_key, photo)
            self.root.after(0, lambda: self._update_canvas(canvas, photo))
        
        except Exception:
            pass
    
    def _update_canvas(self, canvas, photo):
        """更新画布图片"""
        canvas.delete('all')
        canvas.create_image(THUMBNAIL_SIZE[0]//2, THUMBNAIL_SIZE[1]//2, image=photo)
        canvas.photo = photo
        canvas.loaded = True
    
    def _create_file_thumbnail(self, file_info):
        """创建文件缩略图框架"""
        frame = ttk.Frame(self.scrollable_frame, width=THUMBNAIL_SIZE[0], height=THUMBNAIL_SIZE[1] + 35)
        frame.pack_propagate(False)
        
        # 保存file_info到frame，方便搜索时使用
        frame.file_info = file_info
        
        file_type = file_info['type'].upper()
        
        canvas = tk.Canvas(frame, width=THUMBNAIL_SIZE[0], height=THUMBNAIL_SIZE[1], bg='#f5f5f5', highlightthickness=0)
        canvas.pack(pady=2)
        
        # 绘制默认图标
        if file_info.get('is_folder', False):
            canvas.create_rectangle(5, 10, 115, 100, fill='#4CAF50', outline='#388E3C', width=2)
            canvas.create_polygon(5, 10, 35, 10, 35, 35, fill='#66BB6A', outline='#388E3C', width=2)
            canvas.create_text(60, 60, text="文件夹", fill='white', font=('Arial', 10))
        else:
            canvas.create_rectangle(5, 5, 115, 115, fill='#e0e0e0', outline='#bdbdbd', width=2)
            canvas.create_text(60, 60, text=file_type, fill='#757575', font=('Arial', 12))
        
        name_label = ttk.Label(frame, text=file_info['name'], wraplength=THUMBNAIL_SIZE[0], 
                              justify=tk.CENTER, font=('Arial', 8))
        name_label.pack(pady=2)
        
        canvas.file_info = file_info
        canvas.loaded = False
        
        # 绑定事件
        canvas.bind('<Button-3>', lambda e, info=file_info: self._show_context_menu(e, info))
        canvas.bind('<Double-1>', lambda e, info=file_info: self._zoom_thumbnail(info))
        
        return frame
    
    def _zoom_thumbnail(self, file_info):
        """双击放大查看"""
        zoom_window = tk.Toplevel(self.root)
        zoom_window.title(f"预览: {file_info['name']}")
        zoom_window.geometry("900x700")
        zoom_window.minsize(400, 300)
        
        # 初始化内容框架
        content_frame = ttk.Frame(zoom_window)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        loading_label = ttk.Label(content_frame, text="正在加载...", font=('Arial', 14))
        loading_label.pack(pady=50)
        
        # 保存引用供后续更新使用
        zoom_window.content_frame = content_frame
        zoom_window.file_info = file_info
        zoom_window.content_data = None
        zoom_window.original_image = None  # 缓存原始图片
        zoom_window.resize_timer = None  # 防抖定时器
        zoom_window.last_size = (0, 0)  # 上次渲染的尺寸
        
        def async_load():
            try:
                response = self.http_client.get(file_info['url'])
                zoom_window.content_data = response.content
                
                # 缓存原始图片对象（针对图片类型）
                file_type = file_info['type'].upper()
                if file_type in IMAGE_TYPES:
                    zoom_window.original_image = Image.open(io.BytesIO(response.content))
                
                self.root.after(0, lambda: self._show_zoom_content(zoom_window))
            except Exception as e:
                self.root.after(0, lambda: loading_label.config(text=f"加载失败: {str(e)[:50]}"))
        
        # 绑定窗口大小变化事件（使用防抖）
        zoom_window.bind('<Configure>', lambda e: self._on_zoom_resize_debounce(zoom_window))
        
        thread = threading.Thread(target=async_load)
        thread.daemon = True
        thread.start()
    
    def _on_zoom_resize_debounce(self, zoom_window):
        """窗口大小变化防抖处理"""
        # 清除之前的定时器
        if zoom_window.resize_timer:
            self.root.after_cancel(zoom_window.resize_timer)
        
        # 200ms后执行实际的调整
        zoom_window.resize_timer = self.root.after(200, lambda: self._on_zoom_resize(zoom_window))
    
    def _on_zoom_resize(self, zoom_window):
        """窗口大小变化时重新调整内容"""
        if not hasattr(zoom_window, 'content_data') or zoom_window.content_data is None:
            return
        
        # 获取当前尺寸
        current_width = zoom_window.content_frame.winfo_width() - 40
        current_height = zoom_window.content_frame.winfo_height() - 80
        
        # 如果尺寸变化小于10像素，不重新渲染
        if abs(current_width - zoom_window.last_size[0]) < 10 and \
           abs(current_height - zoom_window.last_size[1]) < 10:
            return
        
        # 更新上次尺寸
        zoom_window.last_size = (current_width, current_height)
        
        self._show_zoom_content(zoom_window)
    
    def _show_zoom_content(self, zoom_window):
        """显示放大内容（填充整个窗口）"""
        # 获取当前内容和数据
        content_frame = zoom_window.content_frame
        file_info = zoom_window.file_info
        content = zoom_window.content_data
        
        # 获取实际窗口尺寸（最大化利用空间）
        window_width = content_frame.winfo_width() - 20
        window_height = content_frame.winfo_height() - 60
        
        # 最小尺寸保护
        if window_width < 100 or window_height < 100:
            return
        
        file_type = file_info['type'].upper()
        
        # 清除旧内容
        for widget in content_frame.winfo_children():
            widget.destroy()
        
        if file_type in IMAGE_TYPES:
            try:
                # 使用缓存的原始图片
                if zoom_window.original_image:
                    img = zoom_window.original_image.copy()
                else:
                    img = Image.open(io.BytesIO(content))
                
                width, height = img.size
                
                # 计算缩放比例，让图片清晰且保持宽高比
                # 最小缩放1.5倍，保证清晰度；根据窗口大小智能调整
                ratio_width = window_width / width
                ratio_height = window_height / height
                
                # 如果图片比窗口小，至少放大1.5倍
                if ratio_width > 1.0 and ratio_height > 1.0:
                    ratio = max(1.5, min(ratio_width, ratio_height))
                else:
                    # 如果图片比窗口大，至少显示70%的内容
                    ratio = min(1.5, max(ratio_width, ratio_height, 0.7))
                
                # 应用缩放
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                
                # 创建画布显示图片（带滚动条支持大图片）
                canvas = tk.Canvas(content_frame, bg='#f5f5f5', highlightthickness=0)
                canvas.pack(fill=tk.BOTH, expand=True)
                
                # 设置滚动区域为缩放后的图片大小，确保竖长图片可以完整滚动查看
                canvas.config(scrollregion=(0, 0, new_width, new_height))
                
                # 添加滚动条
                v_scrollbar = ttk.Scrollbar(content_frame, orient=tk.VERTICAL, command=canvas.yview)
                v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                h_scrollbar = ttk.Scrollbar(content_frame, orient=tk.HORIZONTAL, command=canvas.xview)
                h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
                canvas.config(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
                
                # 将画布放到正确位置
                canvas.pack_forget()
                canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                
                canvas.create_image(0, 0, image=photo, anchor=tk.NW)
                canvas.photo = photo
                
            except Exception as e:
                ttk.Label(content_frame, text=f"图片加载失败: {str(e)[:50]}", font=('Arial', 12)).pack(pady=50)
        
        elif file_type in DOC_TYPES:
            try:
                img = DocumentProcessor.create_large_preview(file_type, content, window_width, window_height)
                photo = ImageTk.PhotoImage(img)
                
                # 创建画布显示文档（带滚动条）
                canvas = tk.Canvas(content_frame, bg='#f5f5f5', highlightthickness=0)
                canvas.pack(fill=tk.BOTH, expand=True)
                
                # 设置滚动区域
                canvas.config(scrollregion=(0, 0, img.width, img.height))
                
                # 添加滚动条
                v_scrollbar = ttk.Scrollbar(content_frame, orient=tk.VERTICAL, command=canvas.yview)
                v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                h_scrollbar = ttk.Scrollbar(content_frame, orient=tk.HORIZONTAL, command=canvas.xview)
                h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
                canvas.config(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
                
                # 将画布放到正确位置
                canvas.pack_forget()
                canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                
                canvas.create_image(0, 0, image=photo, anchor=tk.NW)
                canvas.photo = photo
            except Exception as e:
                ttk.Label(content_frame, text=f"文档加载失败: {str(e)[:50]}", font=('Arial', 12)).pack(pady=50)
        
        elif file_type == 'HTML':
            # HTML文件，尝试用浏览器渲染或显示文本
            try:
                # 尝试使用tkhtmlview渲染HTML
                try:
                    from tkhtmlview import HTMLLabel
                    html_label = HTMLLabel(content_frame, html=content.decode('utf-8', errors='replace'))
                    html_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                except ImportError:
                    # 没有安装tkhtmlview，提示用户在浏览器中打开
                    ttk.Label(content_frame, text="HTML文件", font=('Arial', 14)).pack(pady=10)
                    ttk.Label(content_frame, text="建议在浏览器中打开以获得更好的体验", font=('Arial', 12)).pack(pady=5)
                    
                    # 添加在浏览器中打开的按钮
                    def open_in_browser():
                        webbrowser.open(file_info['url'])
                    
                    ttk.Button(content_frame, text="在浏览器中打开", command=open_in_browser).pack(pady=10)
                    
                    # 同时显示HTML源代码
                    ttk.Label(content_frame, text="\nHTML源代码预览:", font=('Arial', 12)).pack(pady=5)
                    text_widget = scrolledtext.ScrolledText(content_frame, wrap=tk.WORD, font=('Consolas', 9))
                    text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
                    text_widget.insert(tk.END, content.decode('utf-8', errors='replace')[:50000])
                    text_widget.config(state=tk.DISABLED)
            except Exception as e:
                ttk.Label(content_frame, text=f"HTML加载失败: {str(e)[:50]}", font=('Arial', 12)).pack(pady=50)
        
        else:
            # 其他类型，显示文本内容
            try:
                text_content = content.decode('utf-8', errors='replace')
                text_widget = scrolledtext.ScrolledText(content_frame, wrap=tk.WORD, font=('Consolas', 10))
                text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                text_widget.insert(tk.END, text_content[:50000])
                text_widget.config(state=tk.DISABLED)
            except Exception as e:
                ttk.Label(content_frame, text=f"无法预览此类型文件: {file_type}", font=('Arial', 12)).pack(pady=50)
    
    def _show_context_menu(self, event, file_info):
        """显示右键菜单"""
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="复制文件URL", command=lambda: self._copy_url(file_info['url']))
        menu.add_command(label="在浏览器中打开", command=lambda: self._open_in_browser(file_info['url']))
        menu.add_command(label="查看文件信息", command=lambda: self._show_file_info(file_info))
        menu.add_command(label="查看所有文件类型", command=self._show_all_file_types)
        menu.post(event.x_root, event.y_root)
    
    def _show_all_file_types(self):
        """显示所有文件的类型信息（调试用）"""
        info = "所有文件类型:\n\n"
        for i, frame in enumerate(self.thumbnail_widgets):
            if hasattr(frame, 'file_info'):
                file_info = frame.file_info
                name = file_info.get('name', '未知')
                file_type = file_info.get('type', '未知')
                info += f"{i}: {name} -> {file_type}\n"
        
        # 只显示前100个文件
        info = info[:5000]
        
        info_window = tk.Toplevel(self.root)
        info_window.title("所有文件类型")
        info_window.geometry("800x600")
        
        text_widget = scrolledtext.ScrolledText(info_window, wrap=tk.WORD, font=('Arial', 10))
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert(tk.END, info)
        text_widget.config(state=tk.DISABLED)
    
    def _copy_url(self, url):
        """复制URL到剪贴板"""
        self.root.clipboard_clear()
        self.root.clipboard_append(url)
        messagebox.showinfo("提示", "URL已复制到剪贴板")
    
    def _open_in_browser(self, url):
        """在浏览器中打开"""
        webbrowser.open(url)
    
    def _show_file_info(self, file_info):
        """显示文件信息"""
        info = f"文件名: {file_info['name']}\n\n类型: {file_info['type']}\n\n大小: {file_info.get('size', '未知')}\n\nURL: {file_info['url']}"
        messagebox.showinfo("文件信息", info)
    
    def _show_load_error(self, error_msg):
        """显示加载错误"""
        messagebox.showerror("加载失败", error_msg)
    
    def _finish_loading(self):
        """完成加载"""
        self.is_loading = False
        self.load_btn.config(state=tk.NORMAL)
    

    
    def view_source(self):
        """查看源码"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("警告", "请输入存储桶URL")
            return
        
        try:
            response = self.http_client.get(url)
            
            source_window = tk.Toplevel(self.root)
            source_window.title(f"源码: {url}")
            source_window.geometry("800x600")
            
            text_widget = scrolledtext.ScrolledText(source_window, wrap=tk.WORD)
            text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            text_widget.insert(tk.END, response.text[:50000])
            text_widget.config(state=tk.DISABLED)
        except Exception as e:
            messagebox.showerror("错误", str(e))
    def __del__(self):
        """清理资源"""
        self.http_client.close()
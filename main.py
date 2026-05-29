#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""存储桶浏览器 - 主入口文件"""

import tkinter as tk
from src.gui.main_window import StorageBrowser


def main():
    """主函数"""
    root = tk.Tk()
    app = StorageBrowser(root)
    root.mainloop()


if __name__ == '__main__':
    main()

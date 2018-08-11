#!/usr/bin/env python

"""
功能：手动生成所有SKU的静态detail html文件
使用方法:
    ./regenerate_index_html.py
"""
import sys
sys.path.insert(0, '../')

# print(sys.path)

import os
if os is not None:
    # os.environ.setdefault, 将系统某个部分环境变量导入到当前任务执行的环境中, key ==> value
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "meiduo_mall.settings.dev")

import django
django.setup()


from contents.crons import generate_static_index_html
# note--项目启动时候已经将apps文件夹导入导包路径了．　所以这里可以直接使用

if __name__ == '__main__':
    generate_static_index_html()





# -*- coding: utf-8 -*-
# @Time : 2022/10/30 10:33
# @Author : 
# @File : logger.py 
# @Software: PyCharm
"""
简易实现输出和保存log
"""
import sys


class LogRecorder:

    def __init__(self):
        self._writing_file = None

    def open_file(self, file_name: str) -> None:
        if '.txt' not in file_name:
            file_name += '.txt'

        self._writing_file = open(file_name, 'w', encoding='utf-8')

    def close_file(self) -> None:
        self._writing_file.close()

    def log_print(self, print_content, *args) -> None:
        if self._writing_file is None:
            print('未创建文件！！！')       # todo: raise Exception
            sys.exit()

        print(print_content)
        self._writing_file.write(str(print_content))
        self._writing_file.write('\n')
        for each_content in args:
            print(each_content)
            self._writing_file.write(str(each_content))
            self._writing_file.write('\n')

    def exit_program(self) -> None:
        """
        实现sys.exit() 功能
        需要先关闭文件
        :return:
        """
        self.close_file()
        sys.exit()

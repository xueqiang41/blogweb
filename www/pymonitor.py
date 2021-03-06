#!/usr/bin/python3
#-*- coding:utf-8  -*-
#pymonitor.py

'''
单独启一个进程，让它监视服务进程。如果www目录下的文件有变化，那么就重启进程。
'''
import os,sys,time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess

def log(s):
    print("[Monitor] %s" % s)
class MyFileSystemEventHandler(FileSystemEventHandler):
    """docstring for MyFileSystemEventHandler"""
    def __init__(self, fn):
        super(MyFileSystemEventHandler, self).__init__()
        self.restart = fn
    def on_any_event(self,event):
        if  event.src_path.endswith(".py"):
            log("Python source has changed:%s" % event.src_path)
            self.restart()

def kill_process():
    global process
    if process:
        log("Kill process %s....." % process.pid)
        process.kill()
        process.wait()
        log("Process end with %s" % process.returncode)
        process = None

def start_process():
    global process,command
    log("Start process %s ..." % command)
    process = subprocess.Popen(command,stdin=sys.stdin,stdout=sys.stdout,stderr=sys.stderr)

def restart_process():
    kill_process()
    start_process()

def start_watch(path):
    #observer也是个进程
    #获取观察对象
    observer = Observer()
    #添加计划，第一个是回调对象，第二个监视路径
    observer.schedule(MyFileSystemEventHandler(restart_process),path,recursive=True)
    observer.start()
    #开始启动子进程
    log("Wathching directory %s...." % path)
    start_process()
    #主进程一直等待
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == '__main__':
    #去掉程序第一参数,python3 pymonitor 或者 ./pymonitor
    argv = sys.argv[1:]

    if not argv:
        print("Usage:python3(or ./) pymonitor app.py")
        exit(0)
    if argv[0] != "python3":
        argv.insert(0,"python3")
    command = argv
    #监听路径
    path = os.path.abspath(".")
    start_watch(path)
    
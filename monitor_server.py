#!/usr/bin/env python3
"""监控导演服务器"""
import subprocess
import sys
import time
import os

def start_server():
    """启动服务器并监控输出"""
    print("=" * 80)
    print("启动导演服务器监控")
    print("=" * 80)
    
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "ui.app:app", "--host", "0.0.0.0", "--port", "8888"],
        cwd=r"K:\AI_Director_Studio_Pack_20260417\AI_Director_Studio",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    print(f"服务器进程 PID: {process.pid}")
    print("监控中... (按 Ctrl+C 停止)\n")
    
    try:
        for line in process.stdout:
            print(line, end='')
            
            # 检测错误
            if "ERROR" in line or "error" in line.lower():
                print(f"\n[!!!] 检测到错误: {line}")
                
    except KeyboardInterrupt:
        print("\n停止监控...")
        process.terminate()
        process.wait()
    
    return process.returncode

if __name__ == "__main__":
    while True:
        return_code = start_server()
        print(f"\n服务器退出，返回码: {return_code}")
        
        if return_code != 0:
            print("服务器异常退出，5秒后重启...")
            time.sleep(5)
        else:
            print("服务器正常退出")
            break

"""诊断 native_ui_app.py 启动失败"""
import sys, os, traceback, time

sys.path.insert(0, r'd:\AI_Director_Studio')
os.chdir(r'd:\AI_Director_Studio')

log_lines = []

def log(msg):
    print(msg)
    log_lines.append(msg)

try:
    log('=== Step 1: 导入 native_ui_app ===')
    import native_ui_app
    log(f'UI_MODE = {native_ui_app.UI_MODE}')
    log(f'CLI_ERROR = {repr(native_ui_app.CLI_ERROR)}')

    if native_ui_app.CLI_ERROR:
        log('!!! CLI_ERROR is not None - 后端加载失败 !!!')
        log(native_ui_app.CLI_ERROR)

    if native_ui_app.cli is None:
        log('!!! cli is None - CLI 不可用 !!!')

    log('=== Step 2: 导入 tkinter / customtkinter ===')
    log(f'ctk available: {native_ui_app.ctk is not None}')
    log(f'UI_MODE: {native_ui_app.UI_MODE}')

    log('=== Step 3: 创建窗口 (3秒后自动退出) ===')
    root = native_ui_app.DirectorStudioApp()
    log(f'窗口创建成功: title={root.title()}, geometry={root.geometry()}')
    root.after(3000, root.destroy)
    root.mainloop()
    log('mainloop 正常退出')

except Exception as e:
    log(f'!!! 异常 !!!')
    log(traceback.format_exc())

finally:
    with open(r'd:\AI_Director_Studio\_diag_result.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(log_lines))
    print('诊断完成，结果写入 _diag_result.txt')

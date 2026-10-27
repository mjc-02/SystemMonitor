# Windows 系统资源监视器

一个使用 Python、PyQt6、psutil 和 pyqtgraph 编写的简单 Windows 系统资源监视器。

## 功能

- 每秒刷新网络上传/下载速率。
- 每秒刷新内存使用率和已用/总容量。
- 每秒刷新磁盘读取/写入速率。
- 绘制最近 60 秒的网络、内存和磁盘曲线。

## 安装与运行

在项目目录打开 PowerShell，执行：

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

如果尚未创建虚拟环境，可以先执行：

```powershell
python -m venv .venv
```

## 测试

```powershell
python -m pytest -q
```

测试也可以在没有 GUI 依赖的情况下使用 Python 标准库运行：

```powershell
python -m unittest discover -s tests -v
```

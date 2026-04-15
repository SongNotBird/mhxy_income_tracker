# 屏幕区域识别点击脚本

这个脚本会持续在屏幕上搜索指定模板图片，匹配到目标样式后，把鼠标移动到匹配到的图片中心并点击。

固定下载页：

```text
https://songnotbird.github.io/mhxy_income_tracker/screen-clicker/
```

适合场景：

- 某个按钮、弹窗、确认界面出现后自动点一下
- 默认全屏搜索目标图片；也可以手动框选一小块搜索范围，减少误判和 CPU 占用
- 先 dry-run 看匹配分数，再启用真正点击

## 安装依赖

```bash
cd /Users/qinliuyu/Documents/小工具/screen_region_clicker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

macOS 第一次运行时，需要给终端或 Python 授权：

- 系统设置 -> 隐私与安全性 -> 屏幕录制
- 系统设置 -> 隐私与安全性 -> 辅助功能

否则脚本可能无法截图或无法控制鼠标。

## Windows 打包 exe

在 Windows 电脑上进入这个文件夹，双击运行：

```text
build_windows.bat
```

首次运行会自动创建 `.venv`、安装依赖和 PyInstaller。打包完成后，exe 在：

```text
dist\ScreenRegionClicker.exe
```

这个 exe 是图形界面版本，可以双击打开；默认关闭 `启用自动点击`，先确认识别分数正常后再打开点击开关。

图形界面里不用手填坐标：

- 点击 `截取目标样式`，主窗口会临时隐藏；在目标按钮或界面元素上拖框，松开后自动保存模板图片
- 多屏幕会按 Windows 虚拟桌面坐标处理，三个屏幕上都可以拖动截取或限制搜索范围
- 默认勾选 `全屏搜索目标图片`，窗口位置漂移也能按图片样式找到目标
- 默认点击 `匹配图片中心`，不依赖固定屏幕坐标
- `启用自动点击` 是独立开关：关闭时只识别和记日志，打开后才真的移动鼠标点击
- 如果误判，可以点击 `拖动限制搜索范围`，只在某一块区域里搜索图片样式
- 按 `Esc` 可以取消截取目标样式、取搜索范围或取备用固定坐标

## 1. 准备目标样式图片

先用系统截图工具截一小块目标界面，保存到 `templates/target.png`。模板最好只包含稳定的界面元素，例如按钮文字、弹窗标题、图标，不要包含会变化的数字、倒计时或动画。

也可以用脚本截取指定区域：

```bash
python screen_clicker.py capture --region 100,200,500,300 --out templates/target.png
```

`--region` 格式是：

```text
X,Y,宽,高
```

## 2. 先测试匹配，不点击

下面命令会全屏搜索 `templates/target.png`，发现目标样式后只打印匹配结果，不移动鼠标：

```bash
python screen_clicker.py watch \
  --template templates/target.png \
  --threshold 0.88 \
  --dry-run \
  --verbose
```

如果目标界面出现时 `score` 经常低于阈值，可以把 `--threshold` 降到 `0.82` 左右；如果误判，就提高到 `0.92` 左右。

## 3. 正式运行并点击

确认 dry-run 正常后，去掉 `--dry-run`：

```bash
python screen_clicker.py watch \
  --template templates/target.png \
  --threshold 0.88
```

默认行为：全屏搜索目标图片，目标界面从没出现变成出现时，点击匹配到的图片中心一次。界面一直停留时不会反复点击。

常用参数：

- `--once`：点击一次后自动退出
- `--repeat`：目标界面持续存在时，也按 `--cooldown` 重复点击
- `--cooldown 5`：两次点击至少间隔 5 秒
- `--pre-click-delay 0.5`：匹配成功后等 0.5 秒再点击
- `--region 100,200,500,300`：只在指定范围里搜索目标图片；不填则全屏搜索
- `--click-center`：点击匹配到的模板中心点，这是默认行为
- `--click-offset 120,40`：点击模板左上角向右 120、向下 40 的位置
- `--click 900,650`：备用的固定坐标点击，不建议窗口会漂移时使用

急停方式：

- 把鼠标快速移动到屏幕左上角，`pyautogui` 会触发急停
- 或者在终端按 `Ctrl+C`

## 示例

全屏搜索模板图片，出现后点击模板中心：

```bash
python screen_clicker.py watch \
  --template templates/target.png
```

只在指定区域里搜索模板图片，出现后点击模板中心：

```bash
python screen_clicker.py watch \
  --region 100,200,500,300 \
  --template templates/target.png
```

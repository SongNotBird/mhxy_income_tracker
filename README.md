# 梦幻西游收益统计

这是一个可打包成 Windows `exe` 的桌面版收益统计工具。

所有数据只保存在你电脑本地的 `data.json`，不会上传到服务器。

功能：

- 道具价格单独管理，录入一次后会长期保存
- 日常统计时只需要选择道具并输入数量
- 点击道具库里的某个物品后，输入数量会自动计算本次收益
- 主窗口改成稳定尺寸，避免拖动后布局错位
- 单价和统计统一使用 `梦幻币`，不再使用“万”
- 点击 `保存本次收获` 后，会记录当天数据并刷新当日统计
- 自动合并当天重复录入的同价道具，减少重复行
- 支持给道具打 `标签`，并在道具库里搜索、筛选
- `常用道具` 改成按条目选择加入，不再一键全量导入
- 自动统计 `当日总计` 和 `总统计`
- 支持录入 `人民币 : 梦幻币` 比例，自动换算当天赚了多少人民币
- 内置 `最近 7 天收益趋势图`
- 支持导出 `CSV`，Excel 可直接打开
- 支持删除当天录错的记录

## 字段说明

- `单价（梦幻币）`：单个道具价格，直接按梦幻币填写
- `标签`：可选，例如 `抓鬼 / 师门 / 副本`
- `人民币比例（元）` 和 `梦幻币比例`：
  例如 `100 元 = 15,000,000 梦幻币`

换算公式：

```text
人民币收益 = 梦幻币总额 / 梦幻币比例 * 人民币比例
```

## 运行源码

```bash
python main.py
```

## Windows 打包 exe

在 Windows 电脑里进入这个目录后，双击运行：

```text
build_windows.bat
```

建议使用 Windows 官方安装版 Python，这样会自带 `tkinter`，打包更稳定。

打包完成后可执行文件在：

```text
dist\MHXYIncomeTracker.exe
```

## 固定发布页

项目里已经带好了：

- GitHub Actions 自动打包 Windows `exe`
- GitHub Releases 自动挂载下载附件
- GitHub Pages 固定下载页

你上传到 GitHub 后，可以得到一个固定网页地址：

```text
https://你的GitHub用户名.github.io/仓库名/
```

这个页面会自动读取当前仓库的最新 Release，并显示 `exe` 下载按钮。

### 首次发布步骤

1. 把整个 `mhxy_income_tracker` 文件夹上传到一个新的 GitHub 仓库
2. 进入仓库 `Settings -> Pages`
3. 在 `Source` 里选择 `GitHub Actions`
4. 推送到默认分支 `main`
5. 进入仓库 `Actions`
6. 运行 `Release Windows EXE`
7. 输入版本号，例如 `v1.0.0`

完成后会同时得到：

- Release 下载页：`https://github.com/你的用户名/仓库名/releases`
- 固定发布页：`https://你的用户名.github.io/仓库名/`

### 后续更新

以后每次更新只需要：

1. 修改代码并推送到 GitHub
2. 再运行一次 `Release Windows EXE`
3. 输入新版本号，例如 `v1.0.1`

固定发布页会自动显示最新版。

## 数据保存位置

- Windows：`%APPDATA%\MHXYIncomeTracker\data.json`
- macOS / Linux：`~/.mhxy_income_tracker/data.json`

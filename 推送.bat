@echo off
chcp 936 >nul
title 推送大肥鱼面板插件到 GitHub
cd /d "%~dp0"
echo ============================================
echo  1) 先在浏览器打开下面这个链接，点最下面的 Create repository
echo     （仓库名必须是 astrbot_plugin_dafeiyu_panel，选 Public）
echo.
echo     https://github.com/new?name=astrbot_plugin_dafeiyu_panel^&description=Dafeiyu+panel:+B站打分台+日记本^&visibility=public
echo ============================================
echo.
pause
echo.
echo 2) 开始推送（第一次会弹 GitHub 登录窗口，登录你自己的账号）
echo.
git push -u origin main
echo.
if errorlevel 1 (
  echo [失败] 请把上面的报错发给我
) else (
  echo [成功] 仓库已推上去，去 https://cloud.astrbot.app/publish 解析它
)
echo.
pause

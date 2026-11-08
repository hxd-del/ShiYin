# 第三方组件与许可声明 / Third-Party Notices

本仓库包含基于上游项目裁剪的第三方代码。分发或公开本仓库时，请同时保留本文件、对应上游许可证与版权声明。

## musicdl 2.14.2

- 上游项目：https://github.com/CharlesPikachu/musicdl
- 作者：Zhenchao Jin
- 许可证：PolyForm Noncommercial License 1.0.0
- 许可证全文：`third_party/musicdl/LICENSE`
- 本仓库位置：`shiyin/vendor/musicdl/`
- 修改说明：按本项目音源白名单裁剪为 41 个音源，移除 DRM、`.wvd`、Apple/TIDAL/SoundCloud 等工具模块；裁剪脚本为 `scripts/build_whitelist.py`，不要手工修改 vendor 目录。
- 重要限制：上游代码采用 **PolyForm Noncommercial 1.0.0**，仅允许非商业用途。任何商业分发、商业使用或再许可，都需要另行取得上游权利人的授权；不能把 `shiyin/vendor/musicdl/` 改成 MIT/Apache 等商业友好许可证。

## Python 依赖

运行依赖见 `requirements-shiyin.txt`，主要包括 PySide6、requests、mutagen 等；这些依赖通过 pip 安装，不随本仓库源码分发。发布安装包或便携包时，请同时遵守各依赖自身的许可证（例如 PySide6 的 LGPL/商业授权条款）。

## 本项目自有代码

本仓库自有代码的许可证尚未在根目录声明。公开到 GitHub 前，请根据你的发布意图补充 `LICENSE`；但只要仓库包含 `shiyin/vendor/musicdl/`，整体分发就需要满足上述非商业限制。

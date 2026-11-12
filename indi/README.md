# RDK X5 上原有的 INDI

QUARCS 连接现有的 `indi.service`，使用端口 `7624`。本目录记录板上已有的 INDI 部署。

| 路径 | 内容 |
| --- | --- |
| `systemd/` | `indi.service` 和板上的三个覆盖文件 |
| `bin/` | QHY 驱动启动脚本，按驱动加载原有 QHY SDK |
| `qhy-ascom/` | 实际运行的本地 QHY 驱动源码、上游对照源码、改动补丁和离线测试 |
| `packages.tsv` | 板上已安装的 INDI 软件包和相关依赖版本 |
| `runtime.sha256` | 当前 INDI 程序和原有 QHY SDK 的 SHA-256 校验值 |

服务加载 LX200 OnStep、V4L2、RoboFocus、Nikon DSLR 和本地 QHY 驱动。`indi_lx200_OnStep` 由 `indi-bin` 提供，`indi_nikon_ccd` 由 `indi-gphoto` 提供。最新的 `95-nikon-dslr.conf` 覆盖启动命令，启用尼康并继续使用本地 QHY 驱动。设备私有配置、SDK 文件和编译产物保存在目标设备上。

## 构建本地 QHY 驱动

在装有对应开发包的 ARM64 RDK X5 上，从仓库根目录执行以下命令。默认链接板上原有的 `libqhyccd.so.26.2.1`。测试使用 SDK 桩函数，无需连接相机。

```sh
cmake -S indi/qhy-ascom -B build/indi-qhy -DCMAKE_BUILD_TYPE=Release
cmake --build build/indi-qhy --parallel 2
ctest --test-dir build/indi-qhy --output-on-failure
```

`qhy-ascom/upstream/` 保存这次本地修改使用的上游对照文件。其余发行版驱动由 INDI 软件包提供，原包版本以 `packages.tsv` 为准。Launchpad 保留了这些历史构建记录，历史源码下载已不可用。

- [INDI 核心上游 v2.2.1](https://github.com/indilib/indi/tree/v2.2.1) 和 [板上 INDI 包的发布记录](https://launchpad.net/~mutlaqja/+archive/ubuntu/ppa/+sourcepub/18397375)
- [INDI 第三方驱动上游](https://github.com/indilib/indi-3rdparty) 和板上 [Nikon/GPhoto](https://launchpad.net/~mutlaqja/+archive/ubuntu/ppa/+sourcepub/18293159)、[QHY](https://launchpad.net/~mutlaqja/+archive/ubuntu/ppa/+sourcepub/18293166) 的原包发布记录

INDI 驱动源码保留原有许可头。发行包的版权说明和 LGPL 许可正文位于 `licenses/`。

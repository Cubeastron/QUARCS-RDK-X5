# QUARCS for RDK X5

这是 QUARCS 在 D-Robotics RDK X5 上运行的版本，使用板上现有的 INDI 服务和 QHY SDK。仓库记录 Qt 后端、Vue 前端、WebSocket 转发、离线星表接口和对应的部署配置。

当前版本包含 INDI 控制面板、尼康相机 ISO、拍摄中止、中文界面、图标修复、离线目标搜索和 OnStep 原生零位操作。OnStep 的同步零位和回零分别使用 `TELESCOPE_HOME.SET` 和 `TELESCOPE_HOME.GO`。

## 目录

| 路径 | 内容 |
| --- | --- |
| `qt/` | Qt 后端及 RDK X5 的 CMake 适配 |
| `web/` | Vue 前端 |
| `hub/` | Node.js WebSocket 转发服务 |
| `search/` | 与 QUARCS 原网页兼容的离线星表 API |
| `deploy/` | RDK X5 的 systemd 和 Nginx 配置 |
| [`indi/`](indi/README.md) | 板上已有的 INDI 服务配置、软件包版本和本地 QHY 驱动源码 |

## 构建

在 ARM64 RDK X5 上构建 Qt 后端，依赖 Qt 5、OpenCV 4、StellarSolver、INDI 开发库、QHY SDK 和 CMake。以下命令以板上已有的库和头文件为例。

```sh
cmake -S qt/src -B build/qt -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_FLAGS_RELEASE="-O1 -DNDEBUG -I$PWD/qt/compat" \
  -DQHYCCD_INCLUDE_DIR=/usr/local/include \
  -DQUARCS_STELLARSOLVER_INCLUDE_DIR=/usr/include/libstellarsolver
cmake --build build/qt --target client --parallel 2
```

构建 Vue 前端。

```sh
cd web
cp .env.example .env
npm ci
node node_modules/@vue/cli-service/bin/vue-cli-service.js build
```

WebSocket 转发服务在 `hub/` 中执行 `npm ci --omit=dev`。服务运行目录为 `/opt/quarcs/hub`，TLS 文件为 `certs/stellarium.crt` 和 `certs/stellarium.key`，在目标板上生成并授予服务用户读取权限。

## 部署路径

| 组件 | 路径或端口 |
| --- | --- |
| Qt 可执行文件 | `/opt/quarcs/bin/client` |
| Qt 工作目录 | `/opt/quarcs/runtime` |
| Vue 产物 | `/var/www/html`，网页端口 `8080` |
| WebSocket | `/opt/quarcs/hub`，端口 `8600` 和 `8601` |
| 离线搜索 | `/opt/quarcs/search`，由 Nginx 在端口 `8090` 转发 |
| INDI | 复用板上的服务，端口 `7624` |

升级已有部署时，用新构建替换 Qt 程序和 Vue 产物，保留目标板上的 `skydata/`、`tiles/`、拍摄目录及运行配置。服务定义与网页站点配置放在 `deploy/`。

首次部署离线搜索时，从自有 QUARCS 镜像内的 `/home/quarcs/workspace/QUARCS/searchapi/` 取出 `dso.txt` 和 `stars_l.txt`，和 `search/server.py` 一起放到 `/opt/quarcs/search/`，然后启用 `quarcs-search.service`。搜索程序使用 Python 3.10 及以上的标准库。

### INDI 启动驱动

将 `deploy/indi-startup.py` 安装到 `/opt/quarcs/bin/`，安装并启用 `quarcs-indi-startup.socket` 及其同名服务单元，再应用 `deploy/nginx/quarcs-rdk.conf`。网页的 INDI 控制面板提供「启动驱动」入口。保存会写入 `/etc/systemd/system/indi.service.d/99-quarcs-drivers.conf`，点击「重启 INDI」后驱动列表生效。重启后可用 QUARCS 的「连接所选设备」重新连接。这个入口管理仓库所用的 QHY、OnStep、尼康、RoboFocus 和 V4L2 驱动。

### 简体中文星图

网页使用现有的语言选项，简体中文模式显示中文方位、星座和常见天体。将 `web/src/assets/sky-zh-cn.json` 与 `search/server.py` 一起安装到 `/opt/quarcs/search/`，然后重启搜索服务，启用中文别名。星表编号和已有英文查询继续可用。

用下列命令为板上已有的西方星图生成可翻译的标签元数据。部署时备份原索引，再用生成的文件替换原索引。

```sh
python3 deploy/localize-western-sky.py \
  /var/www/html/skydata/skycultures/western/index.json /tmp/quarcs-western-index.json
```

网页产物包含离线字体。更新名称表并加入新字符时，用 Python 3.10 及以上版本和 FontTools 从 Noto Sans CJK TTC 重新生成字体子集。

```sh
python3 web/tools/build_sky_font.py \
  /usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc \
  /usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc
```

## 上游源码

| 组件 | 上游提交 |
| --- | --- |
| Qt | [`798d1e5`](https://github.com/QHYCCD-QUARCS/QUARCS_QT-SeverProgram/tree/798d1e56a1a6408fb4c7aacc2cb83bcc36b16378) |
| WebSocket 转发 | [`4b87977`](https://github.com/QHYCCD-QUARCS/QUARCS_NodeJs-Transponder/tree/4b8797760b82139af06a0fc5fc5e1621abc67fd7) |
| Vue 前端与 Stellarium Web Engine | [`71c39ec`](https://github.com/QHYCCD-QUARCS/QUARCS_stellarium-web-engine/tree/71c39ecf7301c4f7a4e325539a2350876a6e4744) |

QUARCS 的上游许可声明保留在各组件目录。INDI 驱动的许可见 `indi/licenses/`。板上的镜像、设备私有配置、TLS 私钥和离线星表数据留在设备或本地备份中。

星图引擎的 JS 和 WASM 从上表的 `71c39ec` 构建。在上游源码目录应用本仓库的 `deploy/stellarium-localized-orbital-labels.patch`，使用 Emscripten 3.1.64 和 SCons 执行 `emscons scons -j8 mode=release werror=no`，再将 `build/stellarium-web-engine.js` 和 `build/stellarium-web-engine.wasm` 一起复制到本仓库的 `web/src/assets/js/`。补丁只在绘制时翻译小行星和彗星的名称，星表标识由原引擎提供。

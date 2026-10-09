#!/usr/bin/env bash
# =============================================================================
#  sq_community 一键安装到 ROS 工作空间
#
#  用法（在虚拟机里执行）：
#     bash install_to_ws.sh              # 自动推断工作空间
#     bash install_to_ws.sh ~/my_ws      # 手动指定工作空间
#
#  自动推断规则：若本脚本位于 <WS>/src/sq_community/，则 <WS> 即为工作空间。
# =============================================================================
set -e

PKG="$(cd "$(dirname "$0")" && pwd)"
PKG_NAME="$(basename "$PKG")"

# 包位于 <WS>/src/<pkg> 时，自动认出 <WS>
AUTO_WS=""
if [ "$(basename "$(dirname "$PKG")")" = "src" ]; then
  AUTO_WS="$(dirname "$(dirname "$PKG")")"
fi

WS="${1:-${AUTO_WS:-$HOME/sq_ws}}"
DISTRO="${ROS_DISTRO:-melodic}"

echo "=============================================="
echo " sq_community 安装器"
echo "   包目录    : $PKG"
echo "   目标空间  : $WS"
echo "   ROS 发行版: $DISTRO"
echo "=============================================="

# ---------------------------------------------------------------- 1/5 同步源码
if [ "$(dirname "$PKG")" = "$WS/src" ]; then
  echo "[1/5] 包已在 $WS/src 下，跳过拷贝"
else
  echo "[1/5] 同步 $PKG  ->  $WS/src/"
  mkdir -p "$WS/src"
  cp -r "$PKG" "$WS/src/"
fi

# 依赖包自检：sq_community 的 launch 依赖 turtlebot3_*，缺了 catkin_make 会失败
MISSING=""
for p in turtlebot3 turtlebot3_msgs turtlebot3_simulations; do
  [ -d "$WS/src/$p" ] || MISSING="$MISSING $p"
done
if [ -n "$MISSING" ]; then
  echo "  !! 警告: $WS/src 下缺少依赖包:$MISSING"
  echo "     请确认压缩包已完整解压（src 下应同时有 sq_community / turtlebot3 /"
  echo "     turtlebot3_msgs / turtlebot3_simulations 四个目录）。"
fi

# ---------------------------------------------------------------- 2/5 系统依赖
echo "[2/5] 安装 ROS 依赖（需要 sudo 密码，已装过的会自动跳过）"
sudo apt-get update -qq || echo "  !! apt-get update 失败，继续尝试安装"
sudo apt-get install -y \
  ros-${DISTRO}-gmapping \
  ros-${DISTRO}-navigation \
  ros-${DISTRO}-map-server \
  ros-${DISTRO}-amcl \
  ros-${DISTRO}-move-base \
  ros-${DISTRO}-dwa-local-planner \
  ros-${DISTRO}-teleop-twist-keyboard \
  ros-${DISTRO}-robot-state-publisher \
  ros-${DISTRO}-cv-bridge \
  ros-${DISTRO}-image-transport \
  ros-${DISTRO}-gazebo-ros \
  ros-${DISTRO}-gazebo-ros-pkgs \
  python-catkin-tools || true

# ---------------------------------------------------------------- 3/5 执行位
echo "[3/5] 给脚本补执行位"
chmod +x "$WS/src/$PKG_NAME"/scripts/*.py 2>/dev/null || true
chmod +x "$WS/src/$PKG_NAME"/tools/*.py 2>/dev/null || true
chmod +x "$WS/src/$PKG_NAME"/install_to_ws.sh 2>/dev/null || true

# ---------------------------------------------------------------- 4/5 编译
echo "[4/5] catkin_make（首次约 1-3 分钟）"
cd "$WS"
catkin_make

# ---------------------------------------------------------------- 5/5 环境
echo "[5/5] 写入 ~/.bashrc"
grep -q "TURTLEBOT3_MODEL" "$HOME/.bashrc" || \
  echo 'export TURTLEBOT3_MODEL=waffle' >> "$HOME/.bashrc"
grep -q "$WS/devel/setup.bash" "$HOME/.bashrc" || \
  echo "source $WS/devel/setup.bash" >> "$HOME/.bashrc"

echo
echo "=============================================="
echo " 完成！请执行:  source ~/.bashrc"
echo " 然后:          roslaunch sq_community sq_community.launch"
echo "=============================================="

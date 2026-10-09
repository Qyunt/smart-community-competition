cmake_minimum_required(VERSION 3.0.2)
project(sq_community)

## 纯资源包：世界文件 / 模型 / launch / python 脚本，无需编译 C++
find_package(catkin REQUIRED)

catkin_package()

install(DIRECTORY launch scripts worlds models docs maps route param rviz tools
        DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
        USE_SOURCE_PERMISSIONS)

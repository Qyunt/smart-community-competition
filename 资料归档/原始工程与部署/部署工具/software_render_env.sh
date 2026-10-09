#!/usr/bin/env bash
# Work around the VMware SVGA/Mesa crash when opening Gazebo 9.
export LIBGL_ALWAYS_SOFTWARE=true
export GALLIUM_DRIVER=llvmpipe
export GAZEBO_MODEL_DATABASE_URI=''

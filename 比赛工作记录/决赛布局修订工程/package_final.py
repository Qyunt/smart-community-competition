from pathlib import Path
import tarfile,zipfile,json,hashlib
p=Path(__file__).resolve().parent
root=p/'src/sq_community'
# Windows edits must not produce CRLF shebangs on Ubuntu.
for path in root.rglob('*'):
    if path.is_file() and path.suffix in ('.py','.sh','.launch','.xacro'):
        path.write_bytes(path.read_bytes().replace(b'\r\n',b'\n'))
with tarfile.open(p/'source_final_install.tar.gz','w:gz') as t:
    for path in root.rglob('*'):
        if not path.is_file() or '__pycache__' in path.parts or path.suffix=='.pyc':continue
        info=t.gettarinfo(str(path),arcname=path.relative_to(root).as_posix())
        info.mode=0o755 if path.suffix in ('.py','.sh') else 0o644
        with path.open('rb') as f:t.addfile(info,f)
dest=p/'智慧社区_决赛布局与预设点_20261009.zip'
with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for path in root.rglob('*'):
        if not path.is_file() or '__pycache__' in path.parts or path.suffix=='.pyc':continue
        info=zipfile.ZipInfo('src/sq_community/'+path.relative_to(root).as_posix())
        info.create_system=3;info.external_attr=((0o100755 if path.suffix in ('.py','.sh') else 0o100644)<<16)
        info.compress_type=zipfile.ZIP_DEFLATED
        z.writestr(info,path.read_bytes())
    z.write(p/'修改说明与预设点.md','修改说明与预设点.md')
    z.writestr('安装说明.txt','此包包含sq_community源码，虚拟机已安装于~/sq_community_ws_20261008。\n新电脑需Ubuntu18.04/ROS Melodic、Gazebo9及package.xml依赖。复制到现有catkin工作空间src后catkin_make。\nWindows工具解压可能丢失Linux权限，运行前执行chmod +x src/sq_community/scripts/*.py。\n开始前阅读修改说明与预设点.md及src/sq_community/SCENE_4P2_README.md。\n原始10×7.2米场景为历史参考；使用带4p2名称的启动文件。\n')
with zipfile.ZipFile(dest) as z:assert z.testzip() is None
(p/'交付文件校验.json').write_text(json.dumps({'filename':dest.name,'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'zip_integrity':'pass'},ensure_ascii=False,indent=2),encoding='utf-8')
print('Packed',dest.name,round(dest.stat().st_size/1048576,2),'MiB')

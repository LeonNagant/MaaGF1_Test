from pathlib import Path
import shutil
import sys
import json
import os

from configure import configure_ocr_model

working_dir = Path(__file__).parent
install_path = working_dir / Path("install")
version = len(sys.argv) > 1 and sys.argv[1] or "v0.0.1"


def install_deps():
    if not (working_dir / "deps" / "bin").exists():
        print("Please download the MaaFramework to \"deps\" first.")
        print("请先下载 MaaFramework 到 \"deps\"。")
        sys.exit(1)

    shutil.copytree(
        working_dir / "deps" / "bin",
        install_path,
        ignore=shutil.ignore_patterns(
            "*MaaDbgControlUnit*",
            "*MaaThriftControlUnit*",
            "*MaaRpc*",
            "*MaaHttp*",
        ),
        dirs_exist_ok=True,
    )
    shutil.copytree(
        working_dir / "deps" / "share" / "MaaAgentBinary",
        install_path / "MaaAgentBinary",
        dirs_exist_ok=True,
    )


def install_resource():
    configure_ocr_model()

    shutil.copytree(
        working_dir / "assets" / "resource",
        install_path / "resource",
        dirs_exist_ok=True,
    )

    shutil.copytree(
        working_dir / "assets" / "resource_en",
        install_path / "resource_en",
        dirs_exist_ok=True,
    )

    shutil.copy2(
        working_dir / "assets" / "interface.json",
        install_path,
    )

    with open(install_path / "interface.json", "r", encoding="utf-8") as f:
        interface = json.load(f)

    interface["version"] = version

    with open(install_path / "interface.json", "w", encoding="utf-8") as f:
        json.dump(interface, f, ensure_ascii=False, indent=4)


def install_chores():
    shutil.copy2(
        working_dir / "README.md",
        install_path,
    )
    shutil.copy2(
        working_dir / "LICENSE",
        install_path,
    )


def install_agent():
    """安装 agent 源码到安装目录"""
    agent_src = working_dir / "agent"
    agent_dst = install_path / "agent"
    
    if not agent_src.exists():
        print("Warning: agent directory not found, skipping agent installation.")
        return
    
    # 创建 agent 目录
    agent_dst.mkdir(parents=True, exist_ok=True)
    
    # 复制 agent 源码文件
    for item in agent_src.iterdir():
        if item.name in ["__pycache__"]:
            continue  # 跳过缓存目录
        
        dst_item = agent_dst / item.name
        if item.is_file():
            shutil.copy2(item, dst_item)
        elif item.is_dir():
            shutil.copytree(item, dst_item, dirs_exist_ok=True)
    
    print(f"Agent source files installed: {agent_src} -> {agent_dst}")


def install_tools():
    """安装工具脚本到安装目录"""
    tools_src = working_dir / "tools"
    tools_dst = install_path / "tools"
    
    if tools_src.exists():
        shutil.copytree(
            tools_src,
            tools_dst,
            dirs_exist_ok=True,
        )
        print(f"Tools installed: {tools_src} -> {tools_dst}")
    else:
        print("Warning: tools directory not found, skipping tools installation.")


if __name__ == "__main__":
    install_deps()
    install_resource()
    install_chores()
    install_agent()
    install_tools()

    print(f"Install to {install_path} successfully.")
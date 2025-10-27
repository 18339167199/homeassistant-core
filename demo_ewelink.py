#!/usr/bin/env python3
"""演示 eWeLink IoT 集成功能的脚本"""

import asyncio
import sys
from pathlib import Path

# 添加 homeassistant 到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

import aiohttp
from homeassistant.components.ewelink_iot.api import (
    EWeLinkApiClient,
    EWeLinkApiError,
    EWeLinkAuthError,
    EWeLinkConnectionError,
)
from homeassistant.components.ewelink_iot.websocket import EWeLinkWebSocketClient


async def demo_api_client():
    """演示 API 客户端功能"""
    print("\n" + "=" * 60)
    print("📡 eWeLink IoT API 客户端演示")
    print("=" * 60 + "\n")

    # 这里使用测试凭证（你需要替换为真实的）
    email = input("请输入 eWeLink 邮箱 (或按 Enter 跳过): ").strip()

    if not email:
        print("\n⚠️  未输入邮箱，使用模拟数据演示...\n")
        demo_mock_data()
        return

    password = input("请输入 eWeLink 密码: ").strip()
    region = input("请输入区域 (cn/as/us/eu, 默认 cn): ").strip() or "cn"

    session = aiohttp.ClientSession()

    try:
        # 创建 API 客户端
        print(f"\n🔧 创建 API 客户端...")
        client = EWeLinkApiClient(
            session=session,
            email=email,
            password=password,
            app_id="4s1FXKC9FaGfoqXhmXSJneb3qcm1gOak",
            app_secret="oKvCM06gvwkRbfetd6qWRrbC3rFrbIpV",
            region=region,
        )

        # 测试登录
        print(f"🔐 正在登录 eWeLink ({region})...")
        try:
            await client.login()
            print(f"✅ 登录成功！")
            print(f"   User ID: {client.user_id}")
            print(
                f"   Token: {client.access_token[:30]}..."
                if client.access_token
                else "   Token: None"
            )
        except EWeLinkAuthError as err:
            print(f"❌ 认证失败: {err}")
            return
        except EWeLinkConnectionError as err:
            print(f"❌ 连接失败: {err}")
            return

        # 获取设备列表
        print(f"\n📱 正在获取设备列表...")
        try:
            devices = await client.get_devices()
            print(f"✅ 获取到 {len(devices)} 个设备\n")

            if not devices:
                print("   (账号下没有设备)")
            else:
                for i, device in enumerate(devices, 1):
                    print(f"   {i}. {device.name}")
                    print(f"      ID: {device.device_id}")
                    print(f"      型号: {device.product_model or 'Unknown'}")
                    print(f"      在线: {'🟢 是' if device.online else '🔴 否'}")
                    print(f"      参数: {device.params}")
                    print()

                    # 检测开关类型
                    if "switches" in device.params:
                        switches = device.params["switches"]
                        print(f"      ➡️ 多通道开关 ({len(switches)} 个通道):")
                        for idx, switch in enumerate(switches):
                            state = (
                                "🟢 开启" if switch.get("switch") == "on" else "🔴 关闭"
                            )
                            print(f"         通道 {idx + 1}: {state}")
                    elif "switch" in device.params:
                        state = (
                            "🟢 开启" if device.params["switch"] == "on" else "🔴 关闭"
                        )
                        print(f"      ➡️ 单通道开关: {state}")
                    print()

        except EWeLinkApiError as err:
            print(f"❌ 获取设备失败: {err}")
            return

        # WebSocket 连接演示
        if devices and client.api_key and client.access_token and client.user_id:
            print(f"\n🔌 WebSocket 连接演示")
            print("-" * 60)

            ws_demo = input("\n是否演示 WebSocket 连接？(y/n): ").strip().lower()
            if ws_demo == "y":
                await demo_websocket(session, client)

    finally:
        await session.close()
        print(f"\n✅ 会话已关闭")


async def demo_websocket(session: aiohttp.ClientSession, client: EWeLinkApiClient):
    """演示 WebSocket 连接"""
    print(f"\n🔌 创建 WebSocket 客户端...")

    ws_client = EWeLinkWebSocketClient(
        session=session,
        api_key=client.api_key or "",
        access_token=client.access_token or "",
        user_id=client.user_id or "",
    )

    try:
        print(f"🔗 正在连接 WebSocket...")
        await ws_client.connect()

        if ws_client.is_connected:
            print(f"✅ WebSocket 连接成功！")
            print(f"\n📡 监听设备状态更新（30秒）...")
            print(f"   在 eWeLink App 中改变设备状态，这里会显示更新消息\n")

            # 监听 30 秒
            await asyncio.sleep(30)

            print(f"\n⏱️  监听结束")
        else:
            print(f"❌ WebSocket 连接失败")

    except Exception as err:
        print(f"❌ WebSocket 错误: {err}")
    finally:
        await ws_client.disconnect()
        print(f"✅ WebSocket 已断开")


def demo_mock_data():
    """演示模拟数据"""
    print("\n📊 模拟设备数据演示\n")

    print("假设 eWeLink 账号下有以下设备：")
    print()
    print("1. 客厅开关")
    print("   ID: 1000abcdef")
    print("   型号: POWR316D")
    print("   在线: 🟢 是")
    print("   类型: 三通道开关")
    print()
    print("   ➡️ 多通道开关 (3 个通道):")
    print("      通道 1: 🟢 开启")
    print("      通道 2: 🔴 关闭")
    print("      通道 3: 🟢 开启")
    print()
    print("在 Home Assistant 中会创建以下实体：")
    print("   • switch.living_room_switch_channel_1  (开启)")
    print("   • switch.living_room_switch_channel_2  (关闭)")
    print("   • switch.living_room_switch_channel_3  (开启)")
    print()
    print("-" * 60)
    print()
    print("2. 卧室灯")
    print("   ID: 1000ghijkl")
    print("   型号: BASICR2")
    print("   在线: 🟢 是")
    print("   类型: 单通道开关")
    print()
    print("   ➡️ 单通道开关: 🔴 关闭")
    print()
    print("在 Home Assistant 中会创建以下实体：")
    print("   • switch.bedroom_light  (关闭)")
    print()


def show_integration_structure():
    """显示集成结构"""
    print("\n" + "=" * 60)
    print("📁 eWeLink IoT 集成文件结构")
    print("=" * 60 + "\n")

    structure = """
homeassistant/components/ewelink_iot/
├── __init__.py          ← 集成入口
├── api.py               ← HTTP API 客户端
├── websocket.py         ← WebSocket 长连接客户端
├── coordinator.py       ← 数据协调器
├── config_flow.py       ← UI 配置流程
├── entity.py            ← 基础实体类
├── switch.py            ← Switch 平台
├── const.py             ← 常量
├── manifest.json        ← 集成元数据
├── strings.json         ← UI 文本
└── quality_scale.yaml   ← 质量配置

tests/components/ewelink_iot/
├── __init__.py
├── conftest.py          ← 测试 fixtures
├── test_config_flow.py  ← 配置流程测试
└── test_init.py         ← 初始化测试
    """
    print(structure)


def show_data_flow():
    """显示数据流程"""
    print("\n" + "=" * 60)
    print("🔄 数据流程")
    print("=" * 60 + "\n")

    flow = """
初始化流程：
  用户配置 → API登录 → 获取设备 → 建立WebSocket → 创建实体

状态更新流程：
  方式1: HTTP 轮询 (每5分钟)
    定时器 → API请求 → 更新数据 → 通知实体 → 前端更新

  方式2: WebSocket 推送 (实时)
    eWeLink推送 → WS接收 → 解析消息 → 更新数据 → 前端立即更新

设备控制流程：
  用户操作 → API请求 → 本地乐观更新 → WS确认 → 最终同步
    """
    print(flow)


async def main():
    """主函数"""
    print("\n" + "🎉" * 30)
    print("   eWeLink IoT 集成功能演示")
    print("🎉" * 30)

    while True:
        print("\n请选择演示内容：")
        print()
        print("  1. API 客户端演示（需要真实账号）")
        print("  2. 查看集成文件结构")
        print("  3. 查看数据流程")
        print("  4. 查看模拟数据演示")
        print("  0. 退出")
        print()

        choice = input("请选择 (0-4): ").strip()

        if choice == "1":
            await demo_api_client()
        elif choice == "2":
            show_integration_structure()
        elif choice == "3":
            show_data_flow()
        elif choice == "4":
            demo_mock_data()
        elif choice == "0":
            print("\n👋 再见！\n")
            break
        else:
            print("\n❌ 无效选择，请重试")

        input("\n按 Enter 继续...")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 用户中断，再见！\n")

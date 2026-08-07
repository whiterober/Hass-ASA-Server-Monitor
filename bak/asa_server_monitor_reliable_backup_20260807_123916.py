# -*- coding: utf-8 -*-
import appdaemon.plugins.hass.hassapi as hass
import aiohttp
import asyncio
import json
import re
import ssl
from datetime import datetime
import socket
import struct

def send_rcon_command_sync(host, port, password, command):
    # 连接并认证
    with socket.create_connection((host, port), timeout=10) as conn:
        # 登录
        def create_packet(request_id, packet_type, payload):
            payload_bytes = payload.encode('utf-8') + b'\x00\x00'
            packet_length = 4 + 4 + len(payload_bytes)
            packet = struct.pack(f'<iii{len(payload_bytes)}s',
                                 packet_length, request_id, packet_type, payload_bytes)
            return packet

        def receive_packets(conn, buffer_size=4096):
            data = b""
            while True:
                part = conn.recv(buffer_size)
                if not part:
                    break
                data += part
                if len(part) < buffer_size:
                    break
            # 只取第一个包
            if len(data) < 12:
                return None
            request_id, response_type = struct.unpack('<ii', data[4:12])
            payload = data[12:-2].decode('utf-8', errors='ignore')
            return request_id, response_type, payload

        # 认证
        login_packet = create_packet(1, 3, password)
        conn.sendall(login_packet)
        login_resp = receive_packets(conn)
        if not login_resp or login_resp[0] == -1:
            return False, "RCON认证失败"
        # 发送命令
        command_packet = create_packet(2, 2, command)
        conn.sendall(command_packet)
        resp = receive_packets(conn)
        if resp:
            return True, resp[2]
        else:
            return False, "无响应"

def strip_markdown(text):
    # 去除常见markdown符号
    text = re.sub(r'<(?!br\s*\/?)[^>]+>', '', text)  # 保留<br>标签
    text = re.sub(r'(\*\*|__|\*|_|`|#+)', '', text)
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'\1', text)  # 去除链接
    text = re.sub(r'>\s?', '', text)  # 去除引用
    text = re.sub(r'!\[(.*?)\]\((.*?)\)', '', text)  # 去除图片
    return text.strip()

class ASAServerMonitorReliable(hass.Hass):
    def initialize(self):

        # 从配置中获取参数
        self.token = self.args.get("token")
        self.base_url = self.args.get("base_url")
        self.profile_names = self.args.get("profile_names", [])
        self.profile_map = self.args.get("profile_map", {})
        self.auto_refresh_interval = self.args.get("auto_refresh_interval", 30)
        self.auto_refresh_delays = self.args.get("auto_refresh_delays", {
            "start": 60,
            "stop": 10,
            "kill": 10,
            "update": 300
        })

        # 新增：动态玩家按钮配置与状态管理
        self.player_button_max_per_server = int(self.args.get("player_button_max_per_server", 8))  # 每服最多生成按钮数，配置可改
        self.generated_player_buttons = {}   # { profile: [entity_id, ...], ...}
        self.player_listeners = {}           # { entity_id: listener_handle, ... }

        self.rcon_host = self.args.get("rcon_host")
        self.rcon_password = self.args.get("rcon_password")
        self.rcon_ports = self.args.get("rcon_ports", {})

        self.refresh_status_interval = int(self.args.get("refresh_status_interval", 0))
        self.log(f"refresh_status_interval: {self.refresh_status_interval}")
        if self.refresh_status_interval > 0:
            self.run_every(self.auto_refresh_status, self.datetime(), self.refresh_status_interval)
        self.log(f"Auto status refresh enabled, interval: {self.refresh_status_interval} seconds")
        
        # 新增：服务器主题配置
        self.server_themes = self.args.get("server_themes", {})
        self.default_theme = self.args.get("default_theme", {})
        
        self.log("ASA Server Monitor (Reliable Version) initialized")
        self.log(f"Base URL: {self.base_url}")
        self.log(f"Profile names: {self.profile_names}")
        self.log(f"Server theme config: {len(self.server_themes)} themes")
        
        # 只创建必要的实体
        self.status_entity = "sensor.asa_server_status"
        self.detail_entity = "sensor.asa_server_details"
        self.theme_entity = "sensor.asa_server_themes"

        # 更新监听器
        self.listen_state(self.update_dialog_server_info, "input_select.selected_server")
        self.listen_state(self.trigger_refresh, "input_button.refresh_server_status")
        #self.listen_state(self.trigger_action, "input_button.execute_server_action")        
        # 添加玩家操作按钮监听
        self.listen_state(self.execute_player_action, "input_button.execute_player_action")
        
        self.listen_state(self.update_profile_port_sensor, "input_select.selected_server")
        
        self.listen_event(self.handle_player_button_event, "call_service", domain="input_button")



        # 初始化实体
        self.initialize_entities()
        self.sync_input_select_options()  # 初始化时同步

        # 初始化后直接刷新
        # self.trigger_refresh(None, None, None, None, {})

        # 延迟开始监控
        self.run_in(self.start_monitoring, 3)

    def update_profile_port_sensor(self, entity, attribute, old, new, kwargs):
        """同步当前选中服务器的端口号到 sensor.profile_port，并写入安全点坐标"""
        profile_ports = self.args.get("profile_ports", {})
        safe_points = self.args.get("safe_points", {})  # 新增
        selected = new or self.get_state("input_select.selected_server")
        port = profile_ports.get(selected, "")
        # 写入端口
        self.set_state(
            "sensor.profile_port",
            state=str(port) if port else "",
            attributes={
                "friendly_name": "当前服务器端口",
                "profile": selected,
                "last_update": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        )
        # 写入安全点坐标
        coords = safe_points.get(selected)
        if coords:
            coords_str = f"{coords['x']} {coords['y']} {coords['z']}"
        else:
            coords_str = ""
        self.set_state(
            "sensor.safe_point_coords",
            state=coords_str,
            attributes={
                "friendly_name": "当前地图安全点坐标",
                "coords": coords_str,
                "profile": selected,
                "last_update": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        )

    def sync_input_select_options(self):
        """同步服务器ID和名称到input_select"""
        server_ids = [""] + self.profile_names
        server_names = ["请选择服务器"] + [self.profile_map.get(sid, sid) for sid in self.profile_names]

        try:
            # 使用 "domain/service" 单字符串形式（斜杠）
            if self.get_state("input_select.selected_server") is not None:
                self.call_service("input_select/set_options",
                                  entity_id="input_select.selected_server",
                                  options=server_ids)
            else:
                self.log("Entity input_select.selected_server not found, skip set_options", level="WARNING")

            if self.get_state("input_select.dialog_server_name") is not None:
                self.call_service("input_select/set_options",
                                  entity_id="input_select.dialog_server_name",
                                  options=server_names)
            else:
                self.log("Entity input_select.dialog_server_name not found, skip set_options", level="WARNING")

            self.log("Synced input_select options for selected_server and dialog_server_name")
        except Exception as e:
            self.log(f"Failed to set input_select options: {e}", level="WARNING")

    def auto_refresh_status(self, kwargs):
        self.log("Scheduled auto refresh server status")
        # 使用 "domain/service" 单字符串形式
        try:
            self.call_service("input_button/press", entity_id="input_button.refresh_server_status")
        except Exception as e:
            self.log(f"Failed to press refresh button: {e}", level="WARNING")

    def initialize_entities(self):
        """初始化所有实体"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 主状态实体
        self.set_state(
            self.status_entity,
            state="初始化中",
            attributes={
                "friendly_name": "ASA服务器状态",
                "icon": "mdi:server",
                "last_update": timestamp,
                "status": "initializing",
                "message": "正在初始化ASA服务器监控器...",
                "execution_status": "初始化中..."
            },
            namespace="default"
        )
        
        # 详细信息实体
        self.set_state(
            self.detail_entity,
            state="加载中...",
            attributes={
                "friendly_name": "ASA服务器详情",
                "icon": "mdi:information",
                "last_update": timestamp,
                "content": "正在初始化ASA服务器监控器...",
                "server_count": 0,
                "online_count": 0,
                "offline_count": 0,
                "profile_ports": self.args.get("profile_ports", {})
            },
            namespace="default"
        )
        
        # 新增：主题配置实体
        self.set_state(
            self.theme_entity,
            state="已加载",
            attributes={
                "friendly_name": "ASA服务器主题配置",
                "icon": "mdi:palette",
                "server_themes": self.server_themes,
                "default_theme": self.default_theme,
                "last_update": timestamp
            },
            namespace="default"
        )

        # 新增：初始化全图存档按钮
        self.set_state(
            "input_button.quan_tu_cun_dang",
            state=self.get_state("input_button.quan_tu_cun_dang") or "unknown",
            attributes={
                "friendly_name": "全图存档",
                "icon": "mdi:content-save-all",
                "status": "尚未执行",
                "last_triggered": None
            },
            namespace="default"
        )

        # 新增：初始化全图清理恐龙按钮
        self.set_state(
            "input_button.quan_tu_qing_li_kong_long",
            state=self.get_state("input_button.quan_tu_qing_li_kong_long") or "unknown",
            attributes={
                "friendly_name": "全图清理恐龙",
                "icon": "mdi:delete-variant",
                "status": "尚未执行",
                "last_triggered": None
            },
            namespace="default"
        )

        self.log("Entities initialized successfully, including theme config and action buttons")

    def start_monitoring(self, kwargs):
        """开始监控"""
        # 监听按钮事件
        try:
            self.listen_state(self.trigger_refresh, "input_button.refresh_server_status")
            self.log("Connected to refresh button")
        except Exception as e:
            self.log(f"Refresh button not found: {e}")
        
        try:
            self.listen_state(self.trigger_action, "input_button.execute_server_action")
            self.log("Connected to execute button")
        except Exception as e:
            self.log(f"Execute button not found: {e}")

        # 监听选中服务器的变化 - 改为input_select
        try:
            self.listen_state(self.update_dialog_server_info, "input_select.selected_server")
            self.log("Connected to selected server listener")
        except Exception as e:
            self.log(f"Selected server entity not found: {e}")

        try:
            self.listen_state(self.trigger_full_save_and_kill, "input_button.quan_tu_cun_dang_hou_zhong_zhi")
            self.log("Connected to full save and kill button")
        except Exception as e:
            self.log(f"Full save and kill button not found: {e}")

        try:
            self.listen_state(self.trigger_save_all_worlds, "input_button.quan_tu_cun_dang")
            self.log("Connected to full save button")
        except Exception as e:
            self.log(f"Full save button not found: {e}")

        try:
            self.listen_event(self.trigger_clear_dinos_all, "call_service", domain="input_button")
            #self.listen_state(self.trigger_clear_dinos_all, "input_button.quan_tu_qing_li_kong_long")
            self.log("Connected to clear dinos button")
        except Exception as e:
            self.log(f"Clear dinos button not found: {e}")
        
        self.log("Monitor started, waiting for manual operation")


    async def safe_select_option(self, entity_id, option, fallback=None):
        """
        在调用 input_select.select_option 前验证 option 是否存在于该 input_select 的 options 中（异步版）。
        若不存在，则选 fallback（若提供）或选第一个 options 项。
        """
        try:
            # 在异步上下文正确 await get_state（AppDaemon 的 get_state 在 async 环境为协程）
            opts = await self.get_state(entity_id, attribute="options")
            # 兼容多种返回类型：None/字符串/列表/字典/tuple
            if not opts:
                opts = []
            elif isinstance(opts, str):
                opts = [opts]
            elif isinstance(opts, dict):
                opts = list(opts.keys())
            elif isinstance(opts, tuple):
                opts = list(opts)

            if option in opts:
                # 使用你要求的单字符串斜杠服务形式
                self.call_service("input_select/select_option", entity_id=entity_id, option=option)
                return True

            # 备选
            target = None
            if fallback and fallback in opts:
                target = fallback
            elif opts:
                target = opts[0]

            if target:
                self.call_service("input_select/select_option", entity_id=entity_id, option=target)
                self.log(f"safe_select_option: option '{option}' not valid for {entity_id}, used fallback '{target}'", level="WARNING")
                return False
            else:
                self.log(f"safe_select_option: no available options for {entity_id} to select.", level="WARNING")
                return False
        except Exception as e:
            self.log(f"safe_select_option error for {entity_id}: {e}", level="ERROR")
            return False


    async def update_dialog_server_info(self, entity, attribute, old, new, kwargs):
        """当选中服务器变化时，更新对话框服务器名称（异步版）"""
        if not new:
            # 使用异步 safe_select_option
            await self.safe_select_option("input_select.dialog_server_name", "请选择服务器")
            return

        try:
            server_name = self.profile_map.get(new, new)
            # 使用异步 safe_select_option 检查并回退
            await self.safe_select_option("input_select.dialog_server_name", server_name, fallback="请选择服务器")
            self.log(f"Selected server updated: {new}")
        except Exception as e:
            self.log(f"Failed to update dialog server name: {e}")

    def trigger_refresh(self, entity, attribute, old, new, kwargs):
        """手动刷新触发器"""
        self.log("Manual refresh triggered")
        # 清空日志并开始新的日志记录
        self.clear_and_start_logging("🔄 开始手动刷新服务器状态")
        self.create_task(self.fetch_and_update_with_logging())
        # 拉取主频道补丁信息
        self.update_patch_description_from_discord()
        # 拉取Patch频道补丁信息
        self.update_patch_channel_info()
        # 拉取新闻频道补丁信息（新增）
        self.update_news_channel_info()
        self.update_tieba_info_from_discord()  # 新增
        self.update_adm_info_from_discord()  # 新增
        self.update_asb_info_from_discord()  # 新增
        # 重新同步 input_select options（使用正确服务名）
        self.sync_input_select_options()
        # 新增：获取当前服务器游戏内时间
        self.create_task(self.fetch_ingame_time_for_all_servers())

    # 新增：获取游戏内时间的方法
    async def fetch_ingame_time_for_all_servers(self):
        """获取所有服务器的游戏内时间"""
        try:
            server_times = {}
            for profile_name in self.profile_names:
                port = self.rcon_ports.get(profile_name)
                if not port:
                    self.log(f"No RCON port configured for {profile_name}", level="WARNING")
                    server_times[profile_name] = "N/A"
                    continue

                # 执行RCON命令 GetInGameTime
                success, result = send_rcon_command_sync(self.rcon_host, port, self.rcon_password, "GetInGameTime")
                if success:
                    # 解析结果，例如 "Day 1, 12:00"
                    ingame_time = result.strip() if result else "N/A"
                    server_times[profile_name] = ingame_time
                    self.log(f"Updated ingame time for {profile_name}: {ingame_time}")
                else:
                    self.log(f"Failed to fetch ingame time for {profile_name}: {result}", level="WARNING")
                    server_times[profile_name] = "获取失败"

            # 更新sensor.ingame_time_cache，存储所有服务器的时间在attributes中
            self.set_state(
                "sensor.ingame_time_cache",
                state="所有服务器时间已更新",
                attributes={
                    "friendly_name": "游戏内时间缓存",
                    "server_times": server_times,
                    "last_update": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            )
        except Exception as e:
            self.log(f"Error fetching ingame times: {e}", level="ERROR")

    def trigger_action(self, entity, attribute, old, new, kwargs):
        """服务器操作触发器"""
        self.log("Server action triggered")
        # 清空日志并开始新的日志记录
        self.clear_and_start_logging("⚡ 开始执行服务器操作")
        self.create_task(self.execute_server_action_with_logging())

    def clear_and_start_logging(self, initial_message):
        """清空日志并开始新的日志会话"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 设置初始日志状态
        self.set_state(
            self.detail_entity,
            state="准备中",
            attributes={
                "friendly_name": "ASA服务器详情",
                "icon": "mdi:console-line",
                "last_update": timestamp,
                "content": f"[{timestamp}] {initial_message}",
                "status": "preparing"
            },
            namespace="default"
        )

    def get_most_common_official_version(self, servers):
        """获取出现频率最高的官方版本"""
        version_counts = {}
        
        for server in servers:
            official_version = server.get("OfficialServerVersion", "N/A")
            if official_version != "N/A":
                # 提取版本号
                version_num = self.extract_version_number(official_version)
                if version_num != "N/A":
                    version_counts[version_num] = version_counts.get(version_num, 0) + 1
        
        if not version_counts:
            return "N/A"
        
        # 返回出现次数最多的版本
        most_common_version = max(version_counts.items(), key=lambda x: x[1])
        return most_common_version[0]

    def format_online_players(self, servers, server_players):
        """格式化在线玩家信息"""
        lines = []
        
        has_online_players = False
        
        for server in servers:
            try:
                profile_name = server.get("ProfileName", "未知")
                map_name = self.profile_map.get(profile_name, profile_name)
                status = server.get("Status", "未知")
                
                if status == "Running":
                    players = server_players.get(profile_name, [])
                    if players:
                        has_online_players = True
                        # 只显示地图中文名
                        lines.append(f"{map_name}")
                        lines.append("-" * len(map_name))
                        
                        for player in players:
                            player_name = player.get("Name", "未知玩家")
                            lines.append(f"  {player_name}")
                        
                        lines.append("")  # 服务器之间空行分隔
            except Exception as e:
                self.log(f"Error formatting player info: {e}", level="ERROR")
                continue
        
        if not has_online_players:
            lines.append("暂无在线玩家")
        
        return "\n".join(lines)

    async def fetch_and_update_with_logging(self):
        """带日志记录的数据获取和更新"""
        self.update_log_display("📡 开始连接服务器API...")

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                retry_info = f" (第 {attempt + 1} 次尝试)" if attempt > 0 else ""
                self.update_log_display(f"🌐 正在获取服务器状态{retry_info}")
                
                # 更新状态实体
                self.set_state(
                    self.status_entity,
                    state="加载中",
                    attributes={
                        "friendly_name": "ASA服务器状态",
                        "icon": "mdi:server",
                        "last_update": timestamp,
                        "status": "loading",
                        "message": f"正在加载服务器状态...{retry_info}"
                    }
                )
                
                # 创建SSL上下文
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False  
                ssl_context.verify_mode = ssl.CERT_NONE
                
                connector = aiohttp.TCPConnector(ssl=ssl_context)
                
                async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=60)) as session:
                    headers = {
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/json"
                    }
                    
                    status_url = f"{self.base_url}/server-status"
                    self.update_log_display(f"🔗 连接地址: {status_url}")
                    
                    async with session.get(status_url, headers=headers) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            servers = data.get("servers", [])
                            self.update_log_display(f"✅ 成功获取 {len(servers)} 个服务器信息")
                            
                            # 获取玩家信息
                            self.update_log_display("👥 正在获取玩家信息...")
                            server_players = await self.fetch_all_players_with_logging(session, servers, headers)
                            #self.log(f"[DEBUG] server_players after fetch: {server_players}")
                            # 新增：生成动态玩家按钮
                            await self.generate_dynamic_player_buttons(server_players)
                            
                            # 计算统计信息
                            self.update_log_display("📊 正在计算统计信息...")
                            official_version = self.get_most_common_official_version(servers)
                            content = self.format_server_status(servers, server_players)
                            compact_content = self.format_compact_status(servers, server_players)
                            
                            online_count = sum(1 for server in servers if server.get("Status") == "Running")
                            offline_count = len(servers) - online_count
                            needs_update = sum(1 for server in servers 
                                            if server.get("ServerVersion", "N/A") != "N/A" and 
                                                server.get("OfficialServerVersion", "N/A") != "N/A" and
                                                server.get("ServerVersion") != server.get("OfficialServerVersion"))
                            total_players = sum(len(players) for players in server_players.values())
                            
                            self.update_log_display("💾 正在更新实体状态...")
                            
                            # 更新主状态实体
                            self.set_state(
                                self.status_entity,
                                state=f"{online_count}/{len(servers)} 在线",
                                attributes={
                                    "friendly_name": "ASA服务器状态",
                                    "icon": "mdi:server" if online_count > 0 else "mdi:server-off",
                                    "last_update": timestamp,
                                    "server_count": len(servers),
                                    "online_count": online_count,
                                    "offline_count": offline_count,
                                    "needs_update_count": needs_update,
                                    "total_players": total_players,
                                    "official_version": official_version,
                                    "status": "success",
                                    "compact_view": compact_content
                                }
                            )

                            # 格式化在线玩家内容
                            online_players_content = self.format_online_players(servers, server_players)
                            
                            # 在成功完成时，修改最终的实体更新：
                            completion_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            
                            # 更新主状态实体 - 集成执行状态到最后更新
                            self.set_state(
                                self.status_entity,
                                state=f"{online_count}/{len(servers)} 在线",
                                attributes={
                                    "friendly_name": "ASA服务器状态",
                                    "icon": "mdi:server" if online_count > 0 else "mdi:server-off",
                                    "last_update": f"{completion_time} ✅ 刷新成功",
                                    "server_count": len(servers),
                                    "online_count": online_count,
                                    "offline_count": offline_count,
                                    "needs_update_count": needs_update,
                                    "total_players": total_players,
                                    "official_version": official_version,
                                    "status": "success",
                                    "compact_view": compact_content,
                                    "execution_status": "✅ 状态刷新成功"  # 添加执行状态
                                }
                            )

                            # 更新主详细信息实体
                            self.set_state(
                                self.detail_entity,
                                state="刷新完成",
                                attributes={
                                    "friendly_name": "ASA服务器详情",
                                    "icon": "mdi:check-circle",
                                    "last_update": completion_time,
                                    "content": f"[{completion_time}] ✅ 刷新执行成功!",
                                    "online_players_content": online_players_content,
                                    "server_count": len(servers),
                                    "online_count": online_count,
                                    "offline_count": offline_count,
                                    "needs_update_count": needs_update,
                                    "total_players": total_players,
                                    "server_players": server_players,
                                    "servers": servers,
                                    "official_version": official_version,
                                    "status": "success",
                                    "profile_ports": self.args.get("profile_ports", {})  # <--- 保持原有
                                }
                            )
                            # 新增：动态生成/清理玩家按钮
                            await self.generate_dynamic_player_buttons(server_players)
                            
                            self.log(f"Entities updated successfully, {len(servers)} servers, {total_players} total online players")
                            
                            # 新增：触发子视图信息更新
                            try:
                                # 在 async 函数中正确 await get_state（避免返回 coroutine/task）
                                current_selected = await self.get_state("input_select.selected_server")
                                if current_selected:
                                    self.log(f"Detected selected server {current_selected}, updating subview info")
                                    # 这里改为 await 异步回调
                                    await self.update_dialog_server_info("input_select.selected_server", None, None, current_selected, {})
                                else:
                                    self.log("No selected server detected, skipping subview update")
                            except Exception as e:
                                self.log(f"Error updating subview info: {str(e)}")


                            
                            return  # 确保在成功完成后返回
                            
                        else:
                            error_msg = f"HTTP {resp.status}: 获取服务器状态失败"
                            self.update_log_display(f"❌ 请求失败: {error_msg}")
                            
                            if attempt < max_retries - 1:
                                self.update_log_display(f"⏳ {retry_delay}秒后进行重试...")
                                await asyncio.sleep
                                continue
                            else:
                                final_error_msg = f"经过 {max_retries} 次重试后仍然失败: {error_msg}"
                                completion_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                
                                # 更新错误状态 - 集成错误信息到最后更新
                                self.set_state(
                                    self.status_entity,
                                    state="错误",
                                    attributes={
                                        "friendly_name": "ASA服务器状态",
                                        "icon": "mdi:server-off",
                                        "last_update": f"{completion_time} ❌ 刷新失败",  # 集成错误状态
                                        "status": "error",
                                        "message": final_error_msg
                                    }
                                )
                                return
                                
            except Exception as e:
                error_msg = f"获取服务器状态时出错: {str(e)}"
                self.update_log_display(f"❌ 异常: {error_msg}")
                
                if attempt < max_retries - 1:
                    self.update_log_display(f"⏳ {retry_delay}秒后进行重试...")
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    final_error_msg = f"经过 {max_retries} 次重试后仍然异常: {error_msg}"
                    completion_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    # 在错误处理中也添加执行状态
                    # 更新错误状态 - 集成错误信息到最后更新
                    self.set_state(
                        self.status_entity,
                        state="错误",
                        attributes={
                            "friendly_name": "ASA服务器状态",
                            "icon": "mdi:server-off",
                            "last_update": f"{completion_time} ❌ 刷新失败",
                            "status": "error",
                            "message": final_error_msg,
                            "execution_status": "❌ 状态刷新失败"  # 添加执行状态
                        }
                    )
                    return                

    async def fetch_all_players_with_logging(self, session, servers, headers):
        """带日志记录的玩家信息获取"""
        server_players = {}
        players_url = f"{self.base_url}/players"
        
        online_servers = [server for server in servers if server.get("Status") == "Running"]
        if not online_servers:
            self.update_log_display("ℹ️ 没有在线服务器，跳过玩家信息获取")
            return server_players
        
        self.update_log_display(f"🎮 发现 {len(online_servers)} 个在线服务器，开始获取玩家信息")
        
        tasks = []
        for server in online_servers:
            profile_name = server.get("ProfileName")
            if profile_name:
                tasks.append(self.fetch_players_for_server_with_retry_and_logging(session, players_url, headers, profile_name))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_players = 0
            for result in results:
                if isinstance(result, tuple) and len(result) == 2:
                    profile_name, players = result
                    server_players[profile_name] = players
                    total_players += len(players)
                elif isinstance(result, Exception):
                    self.update_log_display(f"⚠️ 获取玩家信息时出错: {result}")
            
            self.update_log_display(f"✅ 玩家信息获取完成，共找到 {total_players} 名在线玩家")
        
        return server_players

    async def fetch_players_for_server_with_retry_and_logging(self, session, url, headers, profile_name):
        """带日志记录和重试的单个服务器玩家信息获取"""
        map_name = self.profile_map.get(profile_name, profile_name)
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                payload = {"profileName": profile_name}
                async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        players = data.get("players", [])
                        self.update_log_display(f"🎮 {map_name}: {len(players)} 名玩家在线")
                        return profile_name, players
                    else:
                        error_msg = f"HTTP {resp.status}"
                        self.update_log_display(f"⚠️ {map_name}: 获取玩家信息失败 ({error_msg})")
                        
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_delay)
                            continue
                        else:
                            return profile_name, []
                            
            except asyncio.TimeoutError:
                self.update_log_display(f"⚠️ {map_name}: 获取玩家信息超时")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    return profile_name, []
            except Exception as e:
                self.update_log_display(f"⚠️ {map_name}: 获取玩家信息出错 ({e})")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    return profile_name, []
        
        return profile_name, []

    def update_log_display(self, log_message):
        """更新日志显示 - 只显示最新一条"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 只保留最新一条日志
        new_log_entry = f"[{timestamp}] {log_message}"
        
        # 更新详细信息实体以显示日志
        self.set_state(
            self.detail_entity,
            state="执行中",
            attributes={
                "friendly_name": "ASA服务器详情",
                "icon": "mdi:console-line",
                "last_update": timestamp,
                "content": new_log_entry,  # 只显示当前最新日志
                "status": "logging"
            },
            namespace="default"
        )

    def format_server_status(self, servers, server_players):
        """格式化详细服务器状态"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        lines = []
        lines.append(f"ASA服务器状态 ({timestamp})")
        lines.append("=" * 50)
        
        if not servers:
            return "错误: 未接收到服务器数据"
        
        for server in servers:
            try:
                profile_name = server.get("ProfileName", "未知")
                map_name = self.profile_map.get(profile_name, profile_name)
                status = server.get("Status", "未知")
                server_version = server.get("ServerVersion", "N/A")
                official_version = server.get("OfficialServerVersion", "N/A")
                
                # 获取玩家信息
                players = server_players.get(profile_name, [])
                player_count = len(players)
                
                # 状态指示符
                if status == "Running":
                    status_mark = "[在线]"
                    status_emoji = "🟢"
                elif status == "Stopped":
                    status_mark = "[离线]"
                    status_emoji = "🔴"
                else:
                    status_mark = "[未知]"
                    status_emoji = "❓"
                
                # 版本检查和显示
                version_info = ""
                if server_version != "N/A":
                    # 提取版本号（去掉多余信息）
                    version_num = self.extract_version_number(server_version)
                    official_num = self.extract_version_number(official_version) if official_version != "N/A" else "N/A"
                    
                    if (official_num != "N/A" and version_num != official_num):
                        version_info = f"   版本: {version_num} ⚠️ 需要更新到 {official_num}"
                    else:
                        version_info = f"   版本: {version_num} ✅ 最新"
                else:
                    version_info = "   版本: 未知"
                
                # 玩家信息
                player_info = ""
                if status == "Running":
                    if player_count > 0:
                        player_names = [player.get("Name", "未知") for player in players]
                        player_info = f"   玩家 ({player_count}): {', '.join(player_names)} 👥"
                    else:
                        player_info = "   玩家: 无在线玩家 👥"
                
                lines.append(f"\n{status_emoji} {map_name} ({profile_name})")
                lines.append(f"   状态: {status_mark}")
                if version_info:
                    lines.append(version_info)
                if player_info:
                    lines.append(player_info)
                lines.append("-" * 40)
                
            except Exception as e:
                self.log(f"格式化服务器 {server.get('ProfileName', '未知')} 时出错: {e}", level="ERROR")
                lines.append(f"❌ 错误: {server.get('ProfileName', '未知')}")
                continue
        
        return "\n".join(lines)

    def extract_version_number(self, version_string):
        """提取版本号"""
        if not version_string or version_string == "N/A":
            return "N/A"
        
        # 尝试提取版本号模式，如 "123.456" 或 "123456"
        version_match = re.search(r'(\d+\.?\d*)', str(version_string))
        if version_match:
            return version_match.group(1)
        
        return str(version_string)

    def format_compact_status(self, servers, server_players):
        """格式化紧凑状态"""
        if not servers:
            return "无服务器"
        
        status_list = []
        for server in servers:
            try:
                profile_name = server.get("ProfileName", "未知")
                map_name = self.profile_map.get(profile_name, profile_name)
                status = server.get("Status", "未知")
                
                # 获取玩家数量
                players = server_players.get(profile_name, [])
                player_count = len(players)
                
                if status == "Running":
                    if player_count > 0:
                        status_list.append(f"🟢 {map_name}({player_count})")
                    else:
                        status_list.append(f"🟢 {map_name}(0)")
                elif status == "Stopped":
                    status_list.append(f"🔴 {map_name}")
                else:
                    status_list.append(f"❓ {map_name}")
                    
            except Exception as e:
                self.log(f"紧凑格式出错: {e}")
                continue
        
        return " | ".join(status_list)

    async def execute_server_action_with_logging(self):
        """带日志记录的服务器操作执行"""
        try:
            # 在 async 函数中使用 await get_state（保持不变）
            target_server = await self.get_state("input_select.selected_server")
            action = await self.get_state("input_select.selected_action")
            
            # 处理RCON命令
            rcon_message = ""
            if action == "rcon":
            # 无论如何都直接读取 var.rcon_message 的最新值
                rcon_message = await self.get_state("var.rcon_message")
                self.update_log_display(f"🔍 调试: 当前RCON命令: '{rcon_message}'")
                self.log(f"[DEBUG] rcon_message: {rcon_message}")

                if not rcon_message or not rcon_message.strip():
                    self.update_log_display("❌ RCON命令为空，请先输入命令！")
                    return
                #quick_command = await self.get_state("input_select.rcon_quick_commands")
                #self.update_log_display(f"🔍 调试: 获取到的RCON命令选择: '{quick_command}'")
                #self.log(f"[DEBUG] quick_command: {quick_command}")

                # 优先用 quick_command，如果为空则用 var.rcon_message
                # if quick_command == "自定义命令":
                #     rcon_message = await self.get_state("var.rcon_message")
                #     self.update_log_display(f"🔍 调试: 自定义RCON消息: '{rcon_message}'")
                # elif quick_command and quick_command.strip() != "":
                #     rcon_message = quick_command
                #     try:
                #         self.call_service("var/set", name="rcon_message", value=quick_command)
                #     except Exception:
                #         try:
                #             self.call_service("var/set", entity_id="var.rcon_message", value=quick_command)
                #         except Exception as e:
                #             self.log(f"Failed to set var.rcon_message: {e}", level="WARNING")
                # else:
                    # 如果 quick_command 为空，尝试用 var.rcon_message
                #     rcon_message = await self.get_state("var.rcon_message")
                #     self.update_log_display(f"🔍 调试: 备用RCON消息: '{rcon_message}'")

                #self.update_log_display(f"🔍 调试: 预设RCON消息: '{rcon_message}'")
                #self.log(f"[DEBUG] final rcon_message: {rcon_message}")

                #if not rcon_message:
                #    self.update_log_display("❌ RCON命令为空，请先选择或输入命令！")
                #    return
            
            if not target_server or not action:
                error_msg = f"❌ 错误: 缺少目标服务器或操作参数 (服务器: {target_server}, 操作: {action})"
                self.update_log_display(error_msg)
                return
            
            map_name = self.profile_map.get(target_server, target_server)
            
            action_names = {
                "start": "启动服务器",
                "stop": "停止服务器", 
                "rcon": "RCON命令",
                "saveworld": "保存世界",
                "fullbackup": "完整备份",
                "update": "更新服务器",
                "destroy": "清理恐龙",
                "kill": "强制终止"
            }
            
            action_display = action_names.get(action, action)
            
            self.update_log_display(f"🎯 目标服务器: {map_name} ({target_server})")
            self.update_log_display(f"⚡ 执行操作: {action_display}")
            
            if action == "rcon" and rcon_message:
                self.update_log_display(f"💬 RCON命令: {rcon_message}")
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 更新状态显示操作进行中
            self.set_state(
                self.status_entity,
                state="执行中",
                attributes={
                    "friendly_name": "ASA服务器状态",
                    "icon": "mdi:cog",
                    "last_update": timestamp,
                    "status": "executing",
                    "message": f"正在对 {map_name} 执行 {action_display} 操作..."
                }
            )
            
            # 执行API调用
            self.update_log_display("📡 正在调用服务器API...")
            success, result_message = await self.call_server_api_with_logging(target_server, action, rcon_message)
            
            completion_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if success:
                result_msg = f"✅ {action_display} 在 {map_name} 上执行成功"
                
                self.set_state(
                    self.status_entity,
                    state="操作完成",
                    attributes={
                        "friendly_name": "ASA服务器状态",
                        "icon": "mdi:check",
                        "last_update": f"{completion_time} ✅ 操作成功",
                        "status": "action_completed",
                        "message": result_msg,
                        "last_action": action_display,
                        "last_target": map_name,
                        "last_result": "成功",
                        "execution_status": f"✅ {action_display} 执行成功"
                    }
                )
                
                # 使用配置文件中的自动刷新延迟设置
                if action in self.auto_refresh_delays:
                    delay = self.auto_refresh_delays[action]
                    delay_text = f"{delay // 60}分钟" if delay >= 60 else f"{delay}秒"
                    self.update_log_display(f"🔄 {delay_text}后自动刷新服务器状态...")
                    self.run_in(self.auto_refresh_after_action, delay)
                
            else:
                error_msg = f"❌ {action_display} 在 {map_name} 上执行失败"
                
                self.set_state(
                    self.status_entity,
                    state="操作失败",
                    attributes={
                        "friendly_name": "ASA服务器状态",
                        "icon": "mdi:alert",
                        "last_update": f"{completion_time} ❌ 操作失败",
                        "status": "action_failed",
                        "message": error_msg,
                        "last_action": action_display,
                        "last_target": map_name,
                        "last_result": "失败",
                        "error_details": result_message,
                        "execution_status": f"❌ {action_display} 执行失败"
                    }
                )
                
        except Exception as e:
            error_msg = f"执行服务器操作时出错: {str(e)}"
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            self.set_state(
                self.status_entity,
                state="系统错误",
                attributes={
                    "friendly_name": "ASA服务器状态",
                    "icon": "mdi:alert",
                    "last_update": f"{timestamp} ❌ 系统异常",
                    "status": "system_error",
                    "message": error_msg,
                    "execution_status": "❌ 系统异常"
                }
            )

    def auto_refresh_after_action(self, kwargs):
        """操作后自动刷新"""
        self.log("🔄 操作完成后自动刷新已触发")
        self.clear_and_start_logging("🔄 操作完成后自动刷新服务器状态")
        self.create_task(self.fetch_and_update_with_logging())

    async def call_server_api_with_logging(self, profile_name, action, rcon_message=""):
        if action == "rcon" and rcon_message:
            # 直接本地执行RCON
            host = self.rcon_host
            port = self.rcon_ports.get(profile_name)
            password = self.rcon_password
            if not host or not port or not password:
                return False, "RCON配置不完整"
            try:
                success, result = send_rcon_command_sync(host, port, password, rcon_message)
                if success:
                    self.update_log_display(f"✅ RCON执行成功: {result}")
                    return True, result
                else:
                    self.update_log_display(f"❌ RCON执行失败: {result}")
                    return False, result
            except Exception as e:
                self.update_log_display(f"❌ RCON执行异常: {e}")
                return False, str(e)
        """带日志记录的服务器API调用"""
        max_retries = 3
        retry_delay = 3
        
        for attempt in range(max_retries):
            try:
                retry_info = f" (第 {attempt + 1} 次尝试)" if attempt > 0 else ""
                self.update_log_display(f"🌐 正在调用API{retry_info}")
                
                # 创建SSL上下文
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False  
                ssl_context.verify_mode = ssl.CERT_NONE

                # 针对 destroy/kill 操作延长超时时间
                if action in ["destroy"]:
                    timeout_seconds = 600  # 10分钟
                else:
                    timeout_seconds = 60

                connector = aiohttp.TCPConnector(ssl=ssl_context)
                async with aiohttp.ClientSession(
                    connector=connector,
                    timeout=aiohttp.ClientTimeout(total=timeout_seconds)
                ) as session:
                    headers = {
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/json"
                    }
                    
                    endpoint_map = {
                        "start": "/start",
                        "stop": "/stop", 
                        "players": "/players",
                        "rcon": "/rcon",
                        "saveworld": "/saveworld",
                        "fullbackup": "/fullbackup",
                        "update": "/update",
                        "destroy": "/destroy",
                        "kill": "/kill"
                    }
                    
                    endpoint = endpoint_map.get(action, f"/{action}")
                    api_url = f"{self.base_url}{endpoint}"
                    
                    payload = {"profileName": profile_name}
                    if action == "rcon" and rcon_message:
                        payload["message"] = rcon_message
                    
                    self.update_log_display(f"🔗 API地址: {api_url}")
                    self.update_log_display(f"📦 请求数据: {payload}")
                    self.log(f"[API DEBUG] : {json.dumps(payload, ensure_ascii=False)}")  # 新增日志
                    
                    async with session.post(api_url, json=payload, headers=headers) as resp:
                        self.log(f"[DEBUG] RCON payload: {payload}")
                        response_text = await resp.text()
                        
                        if resp.status == 200:
                            self.update_log_display(f"✅ API调用成功 (HTTP {resp.status})")
                            
                            try:
                                response_data = json.loads(response_text)
                                message = response_data.get("message", "操作执行成功")
                                return True, message
                            except json.JSONDecodeError:
                                return True, response_text
                        else:
                            error_msg = f"HTTP {resp.status}: {response_text}"
                            self.update_log_display(f"❌ API调用失败: {error_msg}")
                            
                            if attempt < max_retries - 1:
                                self.update_log_display(f"⏳ {retry_delay}秒后进行重试...")
                                await asyncio.sleep(retry_delay)
                                continue
                            else:
                                return False, f"经过 {max_retries} 次重试后仍然失败: {error_msg}"
                            
            except asyncio.TimeoutError:
                error_msg = "API调用超时"
                self.update_log_display(f"❌ {error_msg}")
                
                if attempt < max_retries - 1:
                    self.update_log_display(f"⏳ {retry_delay}秒后进行重试...")
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    return False, f"经过 {max_retries} 次重试后仍然超时"
                    
            except Exception as e:
                error_msg = f"API调用异常: {str(e)}"
                self.update_log_display(f"❌ {error_msg}")
                
                if attempt < max_retries - 1:
                    self.update_log_display(f"⏳ {retry_delay}秒后进行重试...")
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    return False, f"经过 {max_retries} 次重试后仍然异常: {str(e)}"
        
        return False, "未知错误"
    
    def trigger_full_save_and_kill(self, entity, attribute, old, new, kwargs):
        """全图存档后终止触发器"""
        self.log("Full save and kill all triggered")
        self.clear_and_start_logging("⚡ 开始执行全图存档后终止")
        self.create_task(self.full_save_and_kill_all())

    async def full_save_and_kill_all(self):
        """依次对所有服务器执行保存世界，然后等待2秒，再执行强制终止"""
        try:
            servers = self.profile_names
            # 1. 全图存档
            for profile in servers:
                self.update_log_display(f"💾 正在对 {self.profile_map.get(profile, profile)} 存档")
                await self.call_server_api_with_logging(profile, "saveworld")
            self.update_log_display("⏳ 等待2秒...")
            await asyncio.sleep(2)
            # 2. 全图强制终止
            for profile in servers:
                self.update_log_display(f"🛑 正在对 {self.profile_map.get(profile, profile)} 强制终止")
                await self.call_server_api_with_logging(profile, "kill")
            self.update_log_display("✅ 全图存档后终止完成")
        except Exception as e:
            self.update_log_display(f"❌ 全图存档后终止异常: {e}")

    async def save_all_worlds(self):
        """对所有服务器执行存档，失败自动重试一次，并更新按钮状态"""
        profile_names = self.profile_names
        profile_map = self.profile_map
        TOKEN = self.token
        URL = f"{self.base_url}/saveworld"

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                tasks = [self.save_profile(session, name, URL, TOKEN) for name in profile_names]
                results = await asyncio.gather(*tasks)

                failed_profiles = [profile_name for profile_name, success, _ in results if not success]

                # 重试失败的
                if failed_profiles:
                    self.log(f"Retrying failed profiles: {failed_profiles}")
                    retry_tasks = [self.save_profile(session, name, URL, TOKEN) for name in failed_profiles]
                    retry_results = await asyncio.gather(*retry_tasks)
                    retry_dict = {profile: (success, message) for profile, success, message in retry_results}
                    final_results = []
                    for profile_name, success, message in results:
                        if profile_name in failed_profiles:
                            retry_success, retry_message = retry_dict[profile_name]
                            final_results.append((profile_name, retry_success, retry_message))
                        else:
                            final_results.append((profile_name, success, message))
                else:
                    final_results = results

                # 统计与格式化
                success_count = sum(1 for _, success, _ in final_results if success)
                total_count = len(profile_names)
                result_details = {}
                for profile_name, success, message in final_results:
                    map_name = profile_map.get(profile_name, profile_name)
                    if success:
                        result_details[map_name] = "✅ 成功"
                    else:
                        short_message = message[:50] + "..." if len(message) > 50 else message
                        result_details[map_name] = f"❌ 失败: {short_message}"

                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                status_text = f"成功: {success_count}/{total_count}"

                # 更新按钮状态
                self.set_state("input_button.quan_tu_cun_dang",
                    state=self.get_state("input_button.quan_tu_cun_dang"),
                    attributes={
                        "friendly_name": "全图存档",
                        "icon": "mdi:content-save-all",
                        "status": status_text,
                        "last_triggered": current_time,
                        "success_count": success_count,
                        "total_count": total_count,
                        "results": result_details
                    }
                )
                self.log(f"Save process completed: {success_count}/{total_count} successful.")
        except Exception as e:
            self.log(f"Error during save_all_worlds: {e}", level="ERROR")
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.set_state("input_button.quan_tu_cun_dang",
                state=self.get_state("input_button.quan_tu_cun_dang"),
                attributes={
                    "friendly_name": "全图存档",
                    "icon": "mdi:content-save-all",
                    "status": f"存档异常: {str(e)}",
                    "last_triggered": current_time
                }
            )

    async def save_profile(self, session, profile_name, url, token):
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {"profileName": profile_name}
        try:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.log(f"Save successful for profile {profile_name}: {data}")
                    return profile_name, True, data.get("message", "保存成功")
                else:
                    error_text = await resp.text()
                    self.log(f"Save failed for profile {profile_name}: {error_text}", level="ERROR")
                    return profile_name, False, error_text
        except Exception as e:
            self.log(f"Error saving profile {profile_name}: {e}", level="ERROR")
            return profile_name, False, str(e)
        
    def trigger_save_all_worlds(self, entity, attribute, old, new, kwargs):
        """全图存档按钮触发"""
        self.log("Full save all triggered")
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.set_state("input_button.quan_tu_cun_dang",
            state=self.get_state("input_button.quan_tu_cun_dang"),
            attributes={
                "friendly_name": "全图存档",
                "icon": "mdi:content-save-all",
                "status": "正在存档中...",
                "last_triggered": current_time
            }
        )
        self.create_task(self.save_all_worlds())

    def trigger_clear_dinos_all(self, event_name, data, kwargs):
        entity_id = data.get("service_data", {}).get("entity_id", "")
        if entity_id == "input_button.quan_tu_qing_li_kong_long":
            self.log("Clear all dinos triggered")
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.set_state("input_button.quan_tu_qing_li_kong_long",
                attributes={
                    "friendly_name": "全图清理恐龙",
                    "icon": "mdi:delete-variant",
                    "status": "正在清理中...",
                    "last_triggered": current_time
                }
            )
            self.create_task(self.clear_dinos_all())

    async def clear_dinos_all(self):
        """对所有服务器同时执行清理恐龙命令（并发调用/destroy接口）"""
        profile_names = self.profile_names
        profile_map = self.profile_map

        try:
            tasks = []
            for profile in profile_names:
                self.update_log_display(f"🧹 正在清理 {profile_map.get(profile, profile)} 的恐龙")
                # 并发调用
                tasks.append(self.call_server_api_with_logging(profile, "destroy"))
            # 并发等待所有结果
            results = await asyncio.gather(*tasks, return_exceptions=True)

            result_details = {}
            for idx, (profile, result) in enumerate(zip(profile_names, results)):
                map_name = profile_map.get(profile, profile)
                if isinstance(result, Exception):
                    result_details[map_name] = f"❌ 异常: {str(result)}"
                else:
                    success, message = result
                    if success:
                        result_details[map_name] = f"✅ {message}"
                    else:
                        short_message = message[:50] + "..." if message and len(message) > 50 else message
                        result_details[map_name] = f"❌ 失败: {short_message}"

            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status_text = "清理完成"

            self.set_state("input_button.quan_tu_qing_li_kong_long",
                state=self.get_state("input_button.quan_tu_qing_li_kong_long"),
                attributes={
                    "friendly_name": "全图清理恐龙",
                    "icon": "mdi:delete-variant",
                    "status": status_text,
                    "last_triggered": current_time,
                    "results": result_details
                }
            )
            self.log("Clear all dinos completed")
        except Exception as e:
            self.log(f"Error during clear_dinos_all: {e}", level="ERROR")
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.set_state("input_button.quan_tu_qing_li_kong_long",
                state=self.get_state("input_button.quan_tu_qing_li_kong_long"),
                attributes={
                    "friendly_name": "全图清理恐龙",
                    "icon": "mdi:delete-variant",
                    "status": f"异常: {str(e)}",
                    "last_triggered": current_time
                }
            )

    async def send_rcon_command(self, session, profile_name, url, token, command):
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {"profileName": profile_name, "command": command}
        try:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.log(f"RCON success {profile_name}: {data}")
                    return profile_name, True, data.get("message", "已发送")
                else:
                    error_text = await resp.text()
                    self.log(f"RCON failed {profile_name}: {error_text}", level="ERROR")
                    return profile_name, False, error_text
        except Exception as e:
            self.log(f"RCON exception {profile_name}: {e}", level="ERROR")
            return profile_name, False, str(e)

    def process_news_links(self, text):
        """处理新闻链接显示为可点击HTML链接"""
        import re
        # 匹配 https://survivetheark.com/index.php 开头的链接
        pattern = r'(https://survivetheark\.com/index\.php[^\s\)\]]*)'
        #return re.sub(pattern, r'<a href="\1" target="_blank" style="color:#1976d2;">新闻链接</a>', text)
        #return re.sub(pattern, r'<a href="\1" target="_blank"><img src="https://cdn-icons-png.flaticon.com/32/1006/1006771.png" alt="新闻链接" style="vertical-align:middle; margin:0 5px;"/></a>', text)
        links = re.findall(pattern, text)
        # 从文本中移除链接
        cleaned_text = re.sub(pattern, '', text)
        return cleaned_text.strip(), links

    def process_patch_links(self, text):
        """处理补丁链接显示为可点击HTML链接"""
        import re
        # 匹配常见的补丁链接模式，可以根据实际情况调整
        pattern = r'(https://[^\s\)\]]*)'
        links = re.findall(pattern, text)
        # 从文本中移除链接
        cleaned_text = re.sub(pattern, '', text)
        return cleaned_text.strip(), links

    def process_tieba_links(self, text):
        """处理贴吧链接"""
        import re
        # 匹配贴吧常见链接模式
        pattern = r'(https?://[^\s\)\]]*)'
        links = re.findall(pattern, text)
        # 从文本中移除链接
        cleaned_text = re.sub(pattern, '', text)
        return cleaned_text.strip(), links
    
    def create_cards_from_content(self, content_list, content_type="patch"):
        """
        通用的卡片创建函数
        
        Args:
            content_list: 内容列表，可以是字符串列表或包含text和images的字典列表
            content_type: 内容类型 ("patch", "news", "channel", "tieba")
        
        Returns:
            cards: 卡片列表
        """
        cards = []
        
        for i, item in enumerate(content_list):  # 添加 enumerate 来获取索引 i
            # 处理不同的输入格式
            if isinstance(item, dict):
                # 新闻频道格式：包含text和images
                text = item.get("text", "")
                images = item.get("images", [])
                youtube_links = item.get("youtube_links", [])  # 新增获取YouTube链接
            else:
                # 补丁频道格式：纯文本
                text = item
                images = []
                youtube_links = []

            
            lines = text.splitlines() if text and text.strip() else []
            
            if lines:
                # 所有类型都使用第一行作为标题（用<h3>标签）
                first_line = f'<h3>{lines[0]}</h3>'
                body_lines = [first_line]
                remaining_lines = lines[1:]
                start_index = 1
                
                content_links = []
                
                for line in remaining_lines:
                    # 根据内容类型处理链接
                    if content_type == "news":
                        cleaned_line, links = self.process_news_links(line)
                    elif content_type == "tieba":
                        cleaned_line, links = self.process_tieba_links(line)
                    else:
                        cleaned_line, links = self.process_patch_links(line)
                    
                    if cleaned_line:  # 只添加非空行
                        body_lines.append(cleaned_line)
                    content_links.extend(links)
                
                body = "\n".join(body_lines)
            else:
                body = ""
                content_links = []
            
            # 组合内容
            md_content = body.strip()
            
            # 只有当 md_content 不为空时才添加 markdown 卡片
            if md_content:
                cards.append({
                    "type": "markdown",
                    "content": md_content
                })
            
            # 处理图片链接 - 不验证content_type，支持所有类型
            if content_links and images:
                # 过滤掉空图片
                images = [img for img in images if img is not None and img.strip()]
                
                if images:  # 确保有有效图片
                    for i, link in enumerate(content_links):
                        # 如果图片数量少于链接数量，循环使用图片
                        image_index = i % len(images)
                        cards.append({
                            "type": "picture",
                            "image": images[image_index],
                            "tap_action": {
                                "action": "url",
                                "url_path": link
                            },
                            "aspect_ratio": "16:9"
                        })
            
            # 处理只有图片没有链接的情况
            elif not content_links and images:
                # 过滤掉空图片和 YouTube 缩略图
                images = [img for img in images if img and img.strip() and not img.startswith("https://i.ytimg.com")]
                
                if images:  # 确保有有效图片
                    for image in images:
                        cards.append({
                            "type": "picture",
                            "image": image,
                            "tap_action": {
                                "action": "url",
                                "url_path": image  # 点击图片时打开图片本身
                            },
                            "aspect_ratio": "16:9"
                        })

            # 处理YouTube链接（使用bot提供的链接而不是重新提取）
            if youtube_links:
                for youtube_url in youtube_links:
                    # 直接从URL中提取视频ID（简化版本）
                    if "watch?v=" in youtube_url:
                        video_id = youtube_url.split("watch?v=")[1].split("&")[0]
                        if len(video_id) == 11:  # YouTube视频ID固定长度为11
                            self.log(f"Adding YouTube iframe for video ID: {video_id}")
                            cards.append({
                                "type": "iframe",
                                "url": f"https://www.youtube.com/embed/{video_id}",
                                "aspect_ratio": "16:9"
                            })
                        else:
                            self.log(f"Invalid YouTube video ID length: {video_id}", level="WARNING")
                    else:
                        self.log(f"Invalid YouTube URL format: {youtube_url}", level="WARNING")

        return cards

    def update_patch_description_from_discord(self):
        try:
            bot_app = self.get_app("discord_patch_bot")
            if not bot_app:
                self.log("DiscordPatchBot app not found.", level="WARNING")
                return
            patches = bot_app.get_latest_patches()
            if hasattr(patches, "json"):
                patches = patches.json()
            if not patches or not isinstance(patches, list):
                self.log("No patch info from Discord bot.", level="WARNING")
                return

            first_patch = patches[0] if patches else ""
            if isinstance(first_patch, dict):
                first_patch_text = first_patch.get("text", "")
            else:
                first_patch_text = str(first_patch)

            summary = ""
            match = re.search(r"\*\*(.*?)\*\*", first_patch_text)
            if match and match.group(1).strip():
                summary = match.group(1).strip()
            else:
                lines = first_patch_text.split('\n')
                if lines:
                    summary = lines[0].strip()
            if not summary:
                summary = "未知补丁信息"
            summary = strip_markdown(summary[:250])

            # 强制要求 created_at 一定存在，否则抛错
            if not (isinstance(patches, list) and patches and isinstance(patches[0], dict)):
                raise ValueError("update_patch_description_from_discord: expected first patch to be dict with created_at")
            created_at = patches[0].get("created_at")
            if not created_at:
                raise ValueError("update_patch_description_from_discord: missing created_at in first patch")

            # 如果 created_at 是 datetime 对象，转为 ISO 字符串
            if isinstance(created_at, datetime):
                created_at = created_at.isoformat()

            # 写入到 cache 实体 （供 template 读取）
            self.set_state("sensor.patch_cache",
                state=summary,
                attributes={
                    "friendly_name": "补丁摘要缓存",
                    "full_content": first_patch_text,
                    "created_at": created_at,
                    "source": "discord_patch_bot"
                }
            )

            # 同时写入带 cards 的全文实体（不影响 template 摘要）
            cards = self.create_cards_from_content(patches, "patch")
            self.set_state("sensor.patch_description_full",
                state="Latest Patch Description",
                attributes={
                    "friendly_name": "Full Patch Description",
                    "cards": cards,
                    "content": first_patch_text,
                    "created_at": created_at
                }
            )
        except Exception as e:
            self.log(f"Failed to update patch description from Discord: {e}", level="WARNING")

    def update_patch_channel_info(self):
        try:
            bot_app = self.get_app("discord_patch_bot")
            if not bot_app:
                self.log("DiscordPatchBot app not found.", level="WARNING")
                return
            patches = bot_app.get_patch_latest()
            if not patches or not isinstance(patches, list):
                self.log("No patch info from patch channel.", level="WARNING")
                return

            # 取文本
            first_patch_text = ""
            if patches:
                first_item = patches[0]
                if isinstance(first_item, dict):
                    first_patch_text = first_item.get("text", "")
                else:
                    first_patch_text = str(first_item)

            if not first_patch_text:
                self.log("No valid patch text found.", level="WARNING")
                return

            summary = ""
            lines = first_patch_text.split('\n')
            version_line = None
            for line in lines:
                if re.search(r'\d+\.\d+\.\d+\.\d+', line):
                    version_line = line.strip()
                    break
            if version_line:
                summary = version_line
            elif len(lines) > 1 and lines[1].strip():
                summary = lines[1].strip()
            elif lines:
                summary = lines[0].strip()
            else:
                summary = "未知补丁信息"

            summary = strip_markdown(summary[:250])

            # 强制要求 created_at 存在，否则报错
            if not (isinstance(patches, list) and patches and isinstance(patches[0], dict)):
                raise ValueError("update_patch_channel_info: expected first patch to be dict with created_at")
            created_at = patches[0].get("created_at")
            if not created_at:
                raise ValueError("update_patch_channel_info: missing created_at in first patch")
            if isinstance(created_at, datetime):
                created_at = created_at.isoformat()

            # 写入 Patch 频道 cache
            self.set_state("sensor.patch_channel_cache",
                state=summary,
                attributes={
                    "friendly_name": "Patch频道摘要缓存",
                    "full_content": first_patch_text,
                    "created_at": created_at,
                    "source": "discord_patch_bot_patch_channel"
                }
            )

            cards = self.create_cards_from_content(patches, "channel")
            self.set_state("sensor.patch_channel_patch_info",
                state="Patch Channel Info",
                attributes={
                    "friendly_name": "Patch频道补丁信息",
                    "cards": cards,
                    "created_at": created_at
                }
            )
            self.log("Patch channel info updated from Discord bot.")
        except Exception as e:
            self.log(f"Failed to update patch channel info: {e}", level="WARNING")

    def update_news_channel_info(self):
        try:
            bot_app = self.get_app("discord_patch_bot")
            if not bot_app:
                self.log("DiscordPatchBot app not found.", level="WARNING")
                return
            news_items = bot_app.get_news_latest()
            if not news_items or not isinstance(news_items, list):
                self.log("No news info from news channel.", level="WARNING")
                return

            cards = self.create_cards_from_content(news_items, "news")

            summary = ""
            if news_items:
                first_news = news_items[0]
                text = first_news["text"] if isinstance(first_news, dict) else str(first_news)
                match = re.search(r"\*\*(.*?)\*\*", text)
                if match and match.group(1).strip():
                    summary = match.group(1).strip()
                else:
                    lines = text.split('\n')
                    if lines:
                        summary = lines[0].strip()
            if not summary:
                summary = "未知新闻摘要"
            summary = strip_markdown(summary[:250])

            # 强制要求 created_at 存在，否则报错
            if not (isinstance(news_items, list) and news_items and isinstance(news_items[0], dict)):
                raise ValueError("update_news_channel_info: expected first news item to be dict with created_at")
            created_at = news_items[0].get("created_at")
            if not created_at:
                raise ValueError("update_news_channel_info: missing created_at in first news item")
            if isinstance(created_at, datetime):
                created_at = created_at.isoformat()

            # 写入 news cache
            self.set_state("sensor.news_cache",
                state=summary,
                attributes={
                    "friendly_name": "新闻摘要缓存",
                    "full_content": news_items[0] if news_items else "",
                    "cards": cards,
                    "created_at": created_at,
                    "source": "discord_patch_bot_news"
                }
            )

            self.set_state("sensor.news_patch_channel_info",
                state="News Channel Info",
                attributes={
                    "friendly_name": "新闻频道补丁信息",
                    "cards": cards,
                    "created_at": created_at
                }
            )
            self.log("News channel info updated from Discord bot.")
        except Exception as e:
            self.log(f"Failed to update news channel info: {e}", level="WARNING")

    def update_tieba_info_from_discord(self):
        try:
            bot_app = self.get_app("discord_patch_bot")
            if not bot_app:
                self.log("DiscordPatchBot app not found.", level="WARNING")
                return
            tieba_msgs = bot_app.get_tieba_latest()
            if not tieba_msgs or not isinstance(tieba_msgs, list):
                self.log("No tieba info from Discord bot.", level="WARNING")
                return

            first_msg = tieba_msgs[0] if tieba_msgs else ""
            if isinstance(first_msg, dict):
                first_msg_text = first_msg.get("text", "")
            else:
                first_msg_text = str(first_msg)
            summary = ""
            match = re.search(r"\*\*(.*?)\*\*", first_msg_text)
            if match and match.group(1).strip():
                summary = match.group(1).strip()
            else:
                lines = first_msg_text.split('\n')
                if lines:
                    summary = lines[0].strip()
            if not summary:
                summary = "未知贴吧信息"
            summary = strip_markdown(summary[:250])

            # 强制要求 created_at 存在，否则报错
            if not (isinstance(tieba_msgs, list) and tieba_msgs and isinstance(tieba_msgs[0], dict)):
                raise ValueError("update_tieba_info_from_discord: expected first tieba item to be dict with created_at")
            created_at = tieba_msgs[0].get("created_at")
            if not created_at:
                raise ValueError("update_tieba_info_from_discord: missing created_at in first tieba item")
            if isinstance(created_at, datetime):
                created_at = created_at.isoformat()

            # 写入 tieba cache
            self.set_state("sensor.tieba_cache",
                state=summary,
                attributes={
                    "friendly_name": "贴吧摘要缓存",
                    "full_content": first_msg_text,
                    "created_at": created_at,
                    "cards": self.create_cards_from_content(tieba_msgs, "tieba"),
                    "source": "discord_patch_bot_tieba"
                }
            )

            cards = self.create_cards_from_content(tieba_msgs, "tieba")
            self.set_state("sensor.tieba_lz_full",
                state="Latest Tieba LZ Reply",
                attributes={
                    "friendly_name": "贴吧楼主最新回复",
                    "cards": cards,
                    "content": first_msg_text,
                    "created_at": created_at
                }
            )
            self.log("Tieba info updated from Discord bot.")
        except Exception as e:
            self.log(f"Failed to update tieba info from Discord: {e}", level="WARNING")

    def update_adm_info_from_discord(self):
        try:
            bot_app = self.get_app("discord_patch_bot")
            if not bot_app:
                self.log("DiscordPatchBot app not found.", level="WARNING")
                return
            adm_msgs = bot_app.get_adm_latest()
            if not adm_msgs or not isinstance(adm_msgs, list):
                self.log("No ADM info from Discord bot.", level="WARNING")
                return

            first_msg = adm_msgs[0] if adm_msgs else ""
            if isinstance(first_msg, dict):
                first_msg_text = first_msg.get("text", "")
            else:
                first_msg_text = str(first_msg)
            summary = ""
            match = re.search(r"\*\*(.*?)\*\*", first_msg_text)
            if match and match.group(1).strip():
                summary = match.group(1).strip()
            else:
                lines = first_msg_text.split('\n')
                if lines:
                    summary = lines[0].strip()
            if not summary:
                summary = "暂无ADM预告信息"
            summary = strip_markdown(summary[:250])

            # 强制要求 created_at 存在，否则报错
            if not (isinstance(adm_msgs, list) and adm_msgs and isinstance(adm_msgs[0], dict)):
                raise ValueError("update_adm_info_from_discord: expected first adm item to be dict with created_at")
            created_at = adm_msgs[0].get("created_at")
            if not created_at:
                raise ValueError("update_adm_info_from_discord: missing created_at in first adm item")
            if isinstance(created_at, datetime):
                created_at = created_at.isoformat()

            # 写入 adm cache
            self.set_state("sensor.adm_cache",
                state=summary,
                attributes={
                    "friendly_name": "ADM摘要缓存",
                    "full_content": first_msg_text,
                    "created_at": created_at,
                    "cards": self.create_cards_from_content(adm_msgs, "adm"),
                    "source": "discord_patch_bot_adm"
                }
            )

            cards = self.create_cards_from_content(adm_msgs, "adm")
            self.set_state("sensor.adm_preview_full",
                state="ADM Preview",
                attributes={
                    "friendly_name": "ADM预告全文",
                    "cards": cards,
                    "content": first_msg_text,
                    "created_at": created_at
                }
            )
            self.log("ADM info updated from Discord bot.")
        except Exception as e:
            self.log(f"Failed to update ADM info from Discord: {e}", level="WARNING")

    def update_asb_info_from_discord(self):
        try:
            bot_app = self.get_app("discord_patch_bot")
            if not bot_app:
                self.log("DiscordPatchBot app not found.", level="WARNING")
                return
            asb_msgs = bot_app.get_asb_latest()
            if not asb_msgs or not isinstance(asb_msgs, list):
                self.log("No asb info from Discord bot.", level="WARNING")
                return

            first_msg = asb_msgs[0] if asb_msgs else ""
            if isinstance(first_msg, dict):
                first_msg_text = first_msg.get("text", "")
            else:
                first_msg_text = str(first_msg)
            summary = ""
            match = re.search(r"\*\*(.*?)\*\*", first_msg_text)
            if match and match.group(1).strip():
                summary = match.group(1).strip()
            else:
                lines = first_msg_text.split('\n')
                if lines:
                    summary = lines[0].strip()
            if not summary:
                summary = "未知ASB信息"
            summary = strip_markdown(summary[:250])

            # 强制要求 created_at 存在，否则报错
            if not (isinstance(asb_msgs, list) and asb_msgs and isinstance(asb_msgs[0], dict)):
                raise ValueError("update_asb_info_from_discord: expected first asb item to be dict with created_at")
            created_at = asb_msgs[0].get("created_at")
            if not created_at:
                raise ValueError("update_asb_info_from_discord: missing created_at in first asb item")
            if isinstance(created_at, datetime):
                created_at = created_at.isoformat()

            # 写入 asb cache
            self.set_state("sensor.asb_cache",
                state=summary,
                attributes={
                    "friendly_name": "ASB摘要缓存",
                    "full_content": first_msg_text,
                    "created_at": created_at,
                    "cards": self.create_cards_from_content(asb_msgs, "asb"),
                    "source": "discord_patch_bot_asb"
                }
            )

            cards = self.create_cards_from_content(asb_msgs, "asb")
            self.set_state("sensor.asb_full",
                state="Latest ASB Info",
                attributes={
                    "friendly_name": "ASB最新信息",
                    "cards": cards,
                    "content": first_msg_text,
                    "created_at": created_at
                }
            )
            self.log("ASB info updated from Discord bot.")
        except Exception as e:
            self.log(f"Failed to update ASB info from Discord: {e}", level="WARNING")

    async def generate_dynamic_player_buttons(self, server_players):
        """改进的动态玩家按钮生成，兼容 HA 2025.10"""
        try:
            # 1. 获取当前所有玩家按钮实体
            all_entities = await self.get_state()
            existing_player_buttons = []
            
            for entity_id in all_entities.keys():
                if isinstance(entity_id, str) and entity_id.startswith("input_button.player_"):
                    existing_player_buttons.append(entity_id)
            
            # 2. 计算需要的新按钮
            needed_buttons = set()
            for profile_name, players in server_players.items():
                if not players:
                    continue
                    
                limited_players = players[:self.player_button_max_per_server]
                for i, player in enumerate(limited_players):
                    player_name = player.get("Name", "未知玩家")
                    safe_profile = profile_name.lower().replace(" ", "_")
                    import re
                    safe_player = re.sub(r'[^a-zA-Z0-9]', '', player_name.lower())
                    if not safe_player:
                        safe_player = f"player{i}"
                    safe_player = safe_player[:20]
                    entity_id = f"input_button.player_{safe_profile}_{i}_{safe_player}"
                    if len(entity_id) > 60:
                        entity_id = f"input_button.player_{safe_profile}_{i}"
                    needed_buttons.add(entity_id)
            
            # 3. 标记不需要的按钮为 unavailable，而不是删除
            for entity_id in existing_player_buttons:
                if entity_id not in needed_buttons:
                    try:
                        self.set_state(entity_id, 
                            state="unavailable", 
                            attributes={
                                "friendly_name": "已移除的玩家按钮",
                                "icon": "mdi:account-off",
                                "removed": True,
                                "available": False
                            }
                        )
                        self.log(f"[REFRESH] Marked player button as unavailable: {entity_id}")
                    except Exception as e:
                        self.log(f"Failed to mark button as unavailable: {entity_id}, {e}", level="WARNING")
            
            # 4. 创建或更新需要的按钮
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.generated_player_buttons.clear()
            
            for profile_name, players in server_players.items():
                if not players:
                    continue

                map_name = self.profile_map.get(profile_name, profile_name)
                limited_players = players[:self.player_button_max_per_server]
                self.generated_player_buttons[profile_name] = []

                for i, player in enumerate(limited_players):
                    player_name = player.get("Name", "未知玩家")
                    player_id = player.get("ID", "")

                    safe_profile = profile_name.lower().replace(" ", "_")
                    import re
                    safe_player = re.sub(r'[^a-zA-Z0-9]', '', player_name.lower())
                    if not safe_player:
                        safe_player = f"player{i}"
                    safe_player = safe_player[:20]
                    entity_id = f"input_button.player_{safe_profile}_{i}_{safe_player}"
                    if len(entity_id) > 60:
                        entity_id = f"input_button.player_{safe_profile}_{i}"

                    # 直接设置状态，让 AppDaemon 处理实体的创建/更新
                    self.set_state(
                        entity_id,
                        state="available",
                        attributes={
                            "friendly_name": f"{map_name} - {player_name}",
                            "icon": "mdi:account",
                            "player_name": player_name,
                            "player_id": player_id,
                            "server_profile": profile_name,
                            "server_map": map_name,
                            "button_type": "player_action",
                            "last_update": current_time,
                            "available_actions": ["踢出", "封禁", "传送到我", "传送到玩家"],
                            "available": True,
                            "removed": False
                        }
                    )

                    self.generated_player_buttons[profile_name].append(entity_id)

        except Exception as e:
            self.log(f"Error generating dynamic player buttons: {e}", level="ERROR")
            import traceback
            self.log(f"Traceback: {traceback.format_exc()}", level="ERROR")

    def handle_player_button_press(self, entity, attribute, old, new, kwargs):
        """处理玩家按钮点击事件"""
        try:
            # 获取按钮属性
            attrs = self.get_state(entity, attribute="all").get("attributes", {})
            
            player_name = attrs.get("player_name", "未知玩家")
            player_id = attrs.get("player_id", "")
            server_profile = attrs.get("server_profile", "")
            server_map = attrs.get("server_map", "")
            
            self.log(f"Player button pressed: {player_name} on {server_map}")
            
            # 更新按钮状态为"已点击"
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.set_state(
                entity,
                state="已点击",
                attributes={
                    **attrs,
                    "last_clicked": current_time,
                    "click_count": attrs.get("click_count", 0) + 1
                }
            )
            
            # 这里可以扩展具体的玩家操作逻辑
            # 例如：显示玩家操作菜单、执行RCON命令等
            self.show_player_action_dialog(player_name, player_id, server_profile, server_map)
            
        except Exception as e:
            self.log(f"Error handling player button press for {entity}: {e}", level="ERROR")

    def show_player_action_dialog(self, player_name, player_id, server_profile, server_map):
        """显示玩家操作对话框（通过更新特定实体）"""
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 获取当前 var.rcon_message 的值
            rcon_message = self.get_state("var.rcon_message")
            if rcon_message:
                # 匹配：空格+“点击在线玩家昵称替换此处” 或 空格+32位字符，后面是空格或结尾
                new_message = re.sub(
                    r' (点击在线玩家昵称替换此处|[a-fA-F0-9]{32})( |$)',
                    f' {player_id}\\2',
                    rcon_message
                )
            else:
                new_message = f"KickPlayer {player_id}"

            self.call_service(
                "var/set",
                entity_id="var.rcon_message",
                value=new_message
            )

            self.log(f"Player action dialog shown for {player_name} on {server_map}")

        except Exception as e:
            self.log(f"Error showing player action dialog: {e}", level="ERROR")

    def execute_player_action(self, entity, attribute, old, new, kwargs):
        """执行玩家操作"""
        try:
            # 获取当前选中的玩家信息
            dialog_attrs = self.get_state("sensor.player_action_dialog", attribute="all").get("attributes", {})
            
            player_name = dialog_attrs.get("player_name", "")
            player_id = dialog_attrs.get("player_id", "")
            server_profile = dialog_attrs.get("server_profile", "")
            server_map = dialog_attrs.get("server_map", "")
            
            if not all([player_name, player_id, server_profile]):
                self.log("Missing player information for action execution", level="WARNING")
                return
                
            # 获取操作类型和消息（使用 var 替代 input_text）
            action_type = self.get_state("input_select.player_action_type")
            custom_message = self.get_state("var.player_action_message")
            
            # 构建RCON命令
            rcon_command = self.build_player_rcon_command(action_type, player_id, player_name, custom_message)
            
            if rcon_command:
                self.log(f"Executing player action: {action_type} for {player_name} on {server_map}")
                
                # 异步执行RCON命令
                self.create_task(self.execute_player_rcon_command(server_profile, rcon_command, action_type, player_name, server_map))
            else:
                self.log(f"Invalid action type: {action_type}", level="WARNING")
                
        except Exception as e:
            self.log(f"Error executing player action: {e}", level="ERROR")

    def build_player_rcon_command(self, action_type, player_id, player_name, custom_message=""):
        """构建玩家操作的RCON命令"""
        command_map = {
            "踢出玩家": f"KickPlayer {player_id}",
            "封禁玩家": f"BanPlayer {player_id}",
            "传送到玩家": f"TeleportToPlayer {player_id}",
            "传送玩家到我": f"TeleportPlayerIDToMe {player_id}",
            "发送私信": f"ServerChatToPlayer {player_id} {custom_message}" if custom_message else None
        }
        
        return command_map.get(action_type)

    async def execute_player_rcon_command(self, server_profile, rcon_command, action_type, player_name, server_map):
        """异步执行玩家RCON命令"""
        try:
            self.update_log_display(f"🎮 正在对 {player_name} 执行 {action_type}")
            
            success, result = await self.call_server_api_with_logging(server_profile, "rcon", rcon_command)
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if success:
                # 更新执行按钮状态
                self.set_state(
                    "input_button.execute_player_action",
                    state=self.get_state("input_button.execute_player_action"),
                    attributes={
                        "friendly_name": "执行玩家操作",
                        "icon": "mdi:check",
                        "last_action": action_type,
                        "last_player": player_name,
                        "last_server": server_map,
                        "last_result": "成功",
                        "last_update": current_time
                    }
                )
                
                self.update_log_display(f"✅ {action_type} 对 {player_name} 执行成功")
                
                # 5秒后自动刷新服务器状态
                self.run_in(self.auto_refresh_after_action, 5)
                
            else:
                self.set_state(
                    "input_button.execute_player_action",
                    state=self.get_state("input_button.execute_player_action"),
                    attributes={
                        "friendly_name": "执行玩家操作",
                        "icon": "mdi:alert",
                        "last_action": action_type,
                        "last_player": player_name,
                        "last_server": server_map,
                        "last_result": "失败",
                        "last_update": current_time,
                        "error_message": result
                    }
                )
                
                self.update_log_display(f"❌ {action_type} 对 {player_name} 执行失败: {result}")
                
        except Exception as e:
            self.log(f"Error executing player RCON command: {e}", level="ERROR")
            self.update_log_display(f"❌ 执行玩家操作时出错: {e}")

    def handle_player_button_event(self, event_name, data, kwargs):
        # 只处理 input_button.player_* 按钮
        entity_id = data.get("service_data", {}).get("entity_id", "")
        # entity_id 可能是字符串或列表
        if isinstance(entity_id, list):
            entity_ids = entity_id
        else:
            entity_ids = [entity_id]
        for eid in entity_ids:
            if isinstance(eid, str) and eid.startswith("input_button.player_"):
                attrs = self.get_state(eid, attribute="all").get("attributes", {})
                player_name = attrs.get("player_name", "未知玩家")
                player_id = attrs.get("player_id", "")
                server_profile = attrs.get("server_profile", "")
                server_map = attrs.get("server_map", "")
                self.log(f"[event] Player button pressed: {player_name} on {server_map}")
                self.show_player_action_dialog(player_name, player_id, server_profile, server_map)


# ==============================================================================
# Copyright (c) 2026 IT support BD (https://itsupport.com.bd)
# Made By Arif (https://arifmahmud.com/)
# Project: MyAgent | Autonomous Network Ping & Telemetry Sub-Agent
# ==============================================================================

import os
import re
import time
import socket
import asyncio
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("myagent.subagent.ping")

class NetworkPingSubAgent:
    """
    Autonomous Sub-Agent responsible for running network ping checks, latency benchmarks,
    and TCP reachability diagnostics from the Agent Server IP (192.168.9.9) to target IPs.
    """

    DEFAULT_TARGETS = [
        {"ip": "192.168.9.1", "name": "Gateway Router", "port": 80, "type": "icmp"},
        {"ip": "192.168.9.5", "name": "NAS Storage Server", "port": 445, "type": "icmp"},
        {"ip": "192.168.9.9", "name": "Local Host Agent Server", "port": 3399, "type": "icmp"},
        {"ip": "8.8.8.8", "name": "Google Public DNS", "port": 53, "type": "icmp"},
        {"ip": "1.1.1.1", "name": "Cloudflare High-Speed DNS", "port": 53, "type": "icmp"},
    ]

    @classmethod
    def get_server_network_info(cls) -> Dict[str, Any]:
        """Discovers Agent Server's local network IPs, hostname, and default interface."""
        hostname = socket.gethostname()
        local_ip = "127.0.0.1"
        server_ip = os.environ.get("SERVER_IP", "192.168.9.9")
        gateway_ip = "192.168.9.1"

        try:
            # Connect a dummy UDP socket to discover outgoing routing interface
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            try:
                local_ip = socket.gethostbyname(hostname)
            except Exception:
                pass

        return {
            "server_ip": server_ip,
            "container_ip": local_ip,
            "hostname": hostname,
            "gateway_ip": gateway_ip,
            "status": "ONLINE",
            "capabilities": ["ICMP_PING", "TCP_PORT_PING", "BATCH_PROBE", "LATENCY_BENCHMARK"]
        }

    @classmethod
    async def ping_target(
        cls,
        target: str,
        target_name: Optional[str] = None,
        ping_type: str = "icmp",
        port: Optional[int] = None,
        count: int = 3,
        timeout: float = 2.0
    ) -> Dict[str, Any]:
        """
        Executes a ping check against a target host/IP.
        Supports ICMP ping (using system ping) with automated fallback to TCP connect ping.
        """
        target = target.strip()
        server_info = cls.get_server_network_info()
        source_ip = server_info.get("server_ip", "192.168.9.9")

        # Resolve hostname / reverse DNS if possible
        resolved_ip = target
        try:
            resolved_ip = socket.gethostbyname(target)
        except Exception:
            pass

        t0 = time.time()
        
        # 1. ICMP Ping mode
        if ping_type.lower() == "icmp":
            result = await cls._execute_icmp_ping(target, count, timeout)
            # If ICMP fails because binary is missing or blocked, try TCP probe
            if not result.get("success") and (port or result.get("fallback_needed")):
                probe_port = port if port else cls._guess_default_port(target)
                tcp_result = await cls._execute_tcp_ping(resolved_ip, probe_port, count, timeout)
                if tcp_result.get("success"):
                    tcp_result["method"] = f"TCP (Port {probe_port} fallback)"
                    tcp_result["source_server_ip"] = source_ip
                    tcp_result["target_name"] = target_name or target
                    return tcp_result
            
            result["source_server_ip"] = source_ip
            result["target_name"] = target_name or target
            return result

        # 2. TCP Port Ping mode
        probe_port = port if port else cls._guess_default_port(target)
        result = await cls._execute_tcp_ping(resolved_ip, probe_port, count, timeout)
        result["source_server_ip"] = source_ip
        result["target_name"] = target_name or target
        return result

    @classmethod
    async def _execute_icmp_ping(cls, target: str, count: int = 3, timeout: float = 2.0) -> Dict[str, Any]:
        """Executes ICMP ping via subprocess."""
        cmd = ["ping", "-c", str(count), "-W", str(int(max(1, timeout))), target]
        if os.name == 'nt':
            cmd = ["ping", "-n", str(count), "-w", str(int(timeout * 1000)), target]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout * count + 2.0)
            output = stdout.decode(errors="replace") + stderr.decode(errors="replace")
            exit_code = proc.returncode

            # Parse latency metrics
            min_ms, avg_ms, max_ms, mdev_ms = 0.0, 0.0, 0.0, 0.0
            packet_loss = 100.0

            # Match Linux ping: rtt min/avg/max/mdev = 0.045/0.083/0.121/0.038 ms
            rtt_match = re.search(r'(?:rtt|round-trip)\s+min/avg/max/(?:mdev|stddev)\s*=\s*([\d\.]+)/([\d\.]+)/([\d\.]+)/([\d\.]+)\s*ms', output)
            if rtt_match:
                min_ms = float(rtt_match.group(1))
                avg_ms = float(rtt_match.group(2))
                max_ms = float(rtt_match.group(3))
                mdev_ms = float(rtt_match.group(4))

            # Match Windows ping: Minimum = 1ms, Maximum = 4ms, Average = 2ms
            win_match = re.search(r'Minimum\s*=\s*(\d+)ms.*?Maximum\s*=\s*(\d+)ms.*?Average\s*=\s*(\d+)ms', output, re.DOTALL)
            if win_match:
                min_ms = float(win_match.group(1))
                max_ms = float(win_match.group(2))
                avg_ms = float(win_match.group(3))

            # Match packet loss
            loss_match = re.search(r'(\d+)%\s*(?:packet\s*)?loss', output)
            if loss_match:
                packet_loss = float(loss_match.group(1))

            is_online = (exit_code == 0) and (packet_loss < 100.0)
            status = "ONLINE" if is_online else "OFFLINE"
            if is_online and (avg_ms > 100.0 or packet_loss > 0):
                status = "DEGRADED"

            return {
                "success": is_online,
                "status": status,
                "target_ip": target,
                "method": "ICMP",
                "latency_ms": round(avg_ms, 2) if is_online else None,
                "min_ms": round(min_ms, 2) if is_online else None,
                "avg_ms": round(avg_ms, 2) if is_online else None,
                "max_ms": round(max_ms, 2) if is_online else None,
                "jitter_ms": round(mdev_ms, 2) if is_online else None,
                "packet_loss": packet_loss,
                "packets_sent": count,
                "raw_output": output.strip(),
                "fallback_needed": False
            }
        except FileNotFoundError:
            # ping command not installed in minimal container
            return {
                "success": False,
                "status": "OFFLINE",
                "target_ip": target,
                "method": "ICMP",
                "error": "ping binary not found",
                "fallback_needed": True
            }
        except Exception as e:
            return {
                "success": False,
                "status": "OFFLINE",
                "target_ip": target,
                "method": "ICMP",
                "error": str(e),
                "fallback_needed": True
            }

    @classmethod
    async def _execute_tcp_ping(cls, target_ip: str, port: int, count: int = 3, timeout: float = 2.0) -> Dict[str, Any]:
        """Executes a TCP connection ping against target host on specified port."""
        latencies = []
        failures = 0

        for _ in range(count):
            t_start = time.perf_counter()
            try:
                # Run blocking socket connect in threadpool
                loop = asyncio.get_running_loop()
                connected = await loop.run_in_executor(None, cls._sync_socket_connect, target_ip, port, timeout)
                if connected:
                    elapsed = (time.perf_counter() - t_start) * 1000.0
                    latencies.append(elapsed)
                else:
                    failures += 1
            except Exception:
                failures += 1
            await asyncio.sleep(0.05)

        total_probes = count
        packet_loss = round((failures / total_probes) * 100.0, 1)
        is_online = len(latencies) > 0

        avg_ms = sum(latencies) / len(latencies) if latencies else 0.0
        min_ms = min(latencies) if latencies else 0.0
        max_ms = max(latencies) if latencies else 0.0

        status = "ONLINE" if is_online else "OFFLINE"
        if is_online and (avg_ms > 100.0 or packet_loss > 0):
            status = "DEGRADED"

        return {
            "success": is_online,
            "status": status,
            "target_ip": target_ip,
            "port": port,
            "method": f"TCP Port {port}",
            "latency_ms": round(avg_ms, 2) if is_online else None,
            "min_ms": round(min_ms, 2) if is_online else None,
            "avg_ms": round(avg_ms, 2) if is_online else None,
            "max_ms": round(max_ms, 2) if is_online else None,
            "jitter_ms": round(max_ms - min_ms, 2) if is_online else None,
            "packet_loss": packet_loss,
            "packets_sent": total_probes,
            "raw_output": f"TCP Port {port} Handshake: {len(latencies)}/{total_probes} successful ({avg_ms:.2f}ms avg)"
        }

    @staticmethod
    def _sync_socket_connect(ip: str, port: int, timeout: float) -> bool:
        """Synchronous TCP socket connection helper."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            s.connect((ip, port))
            s.close()
            return True
        except Exception:
            return False

    @staticmethod
    def _guess_default_port(target: str) -> int:
        """Smart default port guessing based on common targets."""
        if "9.5" in target:
            return 445  # SMB / Storage
        if "9.9" in target:
            return 3399 # Agent Web Port
        if "8.8.8.8" in target or "1.1.1.1" in target:
            return 53   # DNS
        return 80       # HTTP default

    @classmethod
    async def batch_ping(cls, targets: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Runs concurrent ping checks across a list of target IPs."""
        targets = targets or cls.DEFAULT_TARGETS
        server_info = cls.get_server_network_info()

        tasks = []
        for t in targets:
            ip = t.get("ip") or t.get("target_ip")
            name = t.get("name") or t.get("target_name") or ip
            ping_type = t.get("type") or t.get("ping_type") or "icmp"
            port = t.get("port")
            tasks.append(cls.ping_target(target=ip, target_name=name, ping_type=ping_type, port=port))

        results = await asyncio.gather(*tasks, return_exceptions=False)

        total = len(results)
        online_count = sum(1 for r in results if r.get("status") in ["ONLINE", "DEGRADED"])
        offline_count = total - online_count
        avg_latencies = [r["latency_ms"] for r in results if r.get("latency_ms") is not None]
        fleet_avg_latency = round(sum(avg_latencies) / len(avg_latencies), 2) if avg_latencies else 0.0

        return {
            "server_ip": server_info["server_ip"],
            "container_ip": server_info["container_ip"],
            "hostname": server_info["hostname"],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_targets": total,
            "online_count": online_count,
            "offline_count": offline_count,
            "fleet_avg_latency_ms": fleet_avg_latency,
            "results": results
        }


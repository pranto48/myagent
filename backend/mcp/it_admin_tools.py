# Copyright (c) 2026 IT support BD (https://itsupport.com.bd) | Made By Arif (https://arifmahmud.com/) | Version: 3.5.0
"""
Reliable IT Administrator & Systems/Network Engineering Tools for MyAgent MCP Server.

All tools use pure Python stdlib or pre-installed container libraries (httpx, psutil,
cryptography, iputils-ping) with bounded timeouts, strict input sanitization, and
graceful fallbacks so external or Docker hosts never crash or hang MCP sessions.
"""

import asyncio
import base64
import hashlib
import ipaddress
import json
import logging
import math
import os
import re
import secrets
import socket
import sqlite3
import ssl
import string
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx
from config import settings

logger = logging.getLogger("myagent.mcp.it_admin")

_HOST_PATTERN = re.compile(r"^[A-Za-z0-9.\-_:\[\]]{1,253}$")

_COMMON_PORT_LABELS: Dict[int, str] = {
    21: "FTP",
    22: "SSH",
    23: "Telnet",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    110: "POP3",
    143: "IMAP",
    161: "SNMP",
    389: "LDAP",
    443: "HTTPS",
    445: "SMB/CIFS",
    465: "SMTPS",
    587: "SMTP-Sub",
    636: "LDAPS",
    993: "IMAPS",
    1433: "MSSQL",
    3306: "MySQL",
    3389: "RDP",
    3399: "MyAgent-Web",
    5432: "PostgreSQL",
    6379: "Redis",
    8000: "Backend-API",
    8008: "FastAPI-Alt",
    8080: "HTTP-Proxy",
    8443: "HTTPS-Alt",
    9000: "Portainer",
    9100: "JetDirect-Printer",
    27017: "MongoDB",
}


def _clean_host(raw_host: str) -> str:
    """Extracts and validates a clean hostname or IP without scheme/path."""
    text = (raw_host or "").strip()
    if not text:
        raise ValueError("Host or domain cannot be empty.")
    if "://" in text:
        parsed = urlparse(text)
        text = parsed.hostname or text.split("://", 1)[1]
    text = text.split("/")[0].strip()
    if ":" in text and not text.startswith("["):
        # Strip accidental :port from IPv4/domain
        parts = text.rsplit(":", 1)
        if parts[1].isdigit():
            text = parts[0]
    text = text.strip("[]")
    if not _HOST_PATTERN.match(text):
        raise ValueError(f"Invalid hostname or IP format: '{raw_host}'")
    return text


def _is_ip_address(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


async def _reverse_dns(ip_str: str, timeout_sec: float = 0.8) -> str:
    """Best-effort reverse DNS lookup with short timeout."""
    loop = asyncio.get_running_loop()
    try:
        host, _ = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: socket.getnameinfo((ip_str, 0), 0)),
            timeout=timeout_sec,
        )
        return "" if host == ip_str else host
    except Exception:
        return ""


async def _doh_query(client: httpx.AsyncClient, name: str, rtype: str) -> List[Dict[str, Any]]:
    """Queries DNS records using Cloudflare DoH JSON API with Google DoH fallback."""
    endpoints = [
        ("https://cloudflare-dns.com/dns-query", {"Accept": "application/dns-json"}),
        ("https://dns.google/resolve", {"Accept": "application/json"}),
    ]
    for url, headers in endpoints:
        try:
            resp = await client.get(url, params={"name": name, "type": rtype}, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                answers = data.get("Answer") or []
                return [
                    {
                        "name": a.get("name", name).rstrip("."),
                        "ttl": a.get("TTL", 0),
                        "data": str(a.get("data", "")).strip('"'),
                    }
                    for a in answers
                ]
        except Exception:
            continue
    return []


class ITAdminTools:
    """Suite of reliable IT Administrator & SysAdmin MCP tools."""

    # 1. DNS & Email Record Diagnostics
    @staticmethod
    async def dns_lookup_diagnostics(
        domain: str,
        record_types: Optional[List[str]] = None,
        use_doh: bool = True,
    ) -> str:
        """Resolves local OS DNS (A/AAAA/PTR) plus DoH records (MX, TXT, NS, CNAME, SPF, DMARC)."""
        host = _clean_host(domain)
        loop = asyncio.get_running_loop()

        if _is_ip_address(host):
            rev = await _reverse_dns(host, timeout_sec=2.0)
            ptr_name = ipaddress.ip_address(host).reverse_pointer
            doh_ptr: List[Dict[str, Any]] = []
            if use_doh:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    doh_ptr = await _doh_query(client, ptr_name, "PTR")
            lines = [
                f"### 🌐 Reverse DNS Diagnostics: `{host}`",
                f"- **Reverse Pointer:** `{ptr_name}`",
                f"- **OS PTR Resolution:** `{rev or 'No local PTR record found'}`",
            ]
            if doh_ptr:
                lines.append("- **Public DoH PTR:** " + ", ".join(f"`{r['data']}` (TTL {r['ttl']}s)" for r in doh_ptr))
            return "\n".join(lines)

        requested = [r.strip().upper() for r in (record_types or ["A", "AAAA", "MX", "TXT", "NS", "CNAME"]) if r.strip()]
        local_ips: List[str] = []
        try:
            addr_info = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: socket.getaddrinfo(host, None)),
                timeout=3.0,
            )
            local_ips = sorted({item[4][0] for item in addr_info if item and len(item) > 4})
        except Exception:
            local_ips = []

        doh_results: Dict[str, List[Dict[str, Any]]] = {}
        dmarc_records: List[Dict[str, Any]] = []
        if use_doh:
            async with httpx.AsyncClient(timeout=6.0) as client:
                tasks = {rtype: _doh_query(client, host, rtype) for rtype in requested[:8]}
                if "MX" in requested or "TXT" in requested:
                    tasks["_DMARC"] = _doh_query(client, f"_dmarc.{host}", "TXT")
                gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)
                for key, res in zip(tasks.keys(), gathered):
                    if isinstance(res, list):
                        if key == "_DMARC":
                            dmarc_records = res
                        else:
                            doh_results[key] = res

        lines = [
            f"### 🌐 DNS Diagnostics Report: `{host}`",
            f"- **Local Resolver (Container `/etc/resolv.conf`):** `{', '.join(local_ips) if local_ips else 'Unresolved locally'}`",
        ]

        txt_values = [r["data"] for r in doh_results.get("TXT", [])]
        has_spf = any("v=spf1" in t.lower() for t in txt_values)
        has_dmarc = any("v=dmarc1" in d["data"].lower() for d in dmarc_records)
        if "MX" in requested or "TXT" in requested:
            lines.append(
                f"- **Email Auth Audit:** SPF={'🟢 Found' if has_spf else '🟡 Missing'} | "
                f"DMARC={'🟢 Found' if has_dmarc else '🟡 Missing'}"
            )

        for rtype in requested:
            recs = doh_results.get(rtype, [])
            if recs:
                lines.append(f"\n**{rtype} Records ({len(recs)}):**")
                for r in recs[:15]:
                    lines.append(f"- `{r['data']}` *(TTL: {r['ttl']}s)*")
            elif use_doh:
                lines.append(f"- **{rtype}:** *(No records returned via DoH)*")

        if dmarc_records:
            lines.append("\n**_dmarc TXT Records:**")
            for d in dmarc_records:
                lines.append(f"- `{d['data']}` *(TTL: {d['ttl']}s)*")

        return "\n".join(lines)

    # 2. SSL/TLS Certificate Expiry & Security Inspector
    @staticmethod
    async def ssl_tls_cert_inspector(
        host: str,
        port: int = 443,
        timeout_sec: float = 5.0,
    ) -> str:
        """Inspects live X.509 SSL/TLS certificate expiry, SANs, issuer, cipher, and chain validity."""
        clean_host = _clean_host(host)
        target_port = max(1, min(65535, int(port)))
        timeout = max(1.0, min(15.0, float(timeout_sec)))

        def _fetch_cert() -> Dict[str, Any]:
            from cryptography import x509

            verified_chain = False
            verify_error = ""
            der_bytes: bytes = b""
            tls_version = "Unknown"
            cipher_info: Tuple[str, str, int] = ("Unknown", "Unknown", 0)

            for should_verify in (True, False):
                ctx = ssl.create_default_context()
                if not should_verify:
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                try:
                    with socket.create_connection((clean_host, target_port), timeout=timeout) as sock:
                        with ctx.wrap_socket(sock, server_hostname=clean_host) as ssock:
                            der_bytes = ssock.getpeercert(binary_form=True) or b""
                            tls_version = ssock.version() or "Unknown"
                            c_raw = ssock.cipher()
                            if c_raw:
                                cipher_info = c_raw
                            verified_chain = should_verify
                            break
                except ssl.SSLCertVerificationError as verr:
                    verify_error = str(verr)
                    continue

            if not der_bytes:
                raise RuntimeError(verify_error or f"No TLS certificate presented on {clean_host}:{target_port}")

            cert = x509.load_der_x509_certificate(der_bytes)
            now_utc = datetime.now(timezone.utc)
            not_before = cert.not_valid_before_utc
            not_after = cert.not_valid_after_utc
            days_left = (not_after - now_utc).days

            sans: List[str] = []
            try:
                ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
                sans = [str(n) for n in ext.value.get_values_for_type(x509.DNSName)]
                sans.extend([str(ip) for ip in ext.value.get_values_for_type(x509.IPAddress)])
            except Exception:
                pass

            subject_str = cert.subject.rfc4514_string()
            issuer_str = cert.issuer.rfc4514_string()
            is_self_signed = subject_str == issuer_str
            sha256_fp = hashlib.sha256(der_bytes).hexdigest().upper()
            formatted_fp = ":".join(sha256_fp[i : i + 2] for i in range(0, len(sha256_fp), 2))

            return {
                "subject": subject_str,
                "issuer": issuer_str,
                "sans": sans,
                "not_before": not_before.strftime("%Y-%m-%d %H:%M UTC"),
                "not_after": not_after.strftime("%Y-%m-%d %H:%M UTC"),
                "days_left": days_left,
                "tls_version": tls_version,
                "cipher": f"{cipher_info[0]} ({cipher_info[2]}-bit)",
                "serial_hex": format(cert.serial_number, "X"),
                "sha256_fingerprint": formatted_fp,
                "verified_chain": verified_chain,
                "verify_error": verify_error,
                "self_signed": is_self_signed,
            }

        try:
            info = await asyncio.to_thread(_fetch_cert)
        except Exception as exc:
            return f"### 🔴 SSL/TLS Inspection Failed: `{clean_host}:{target_port}`\n- **Error:** `{exc}`"

        days = info["days_left"]
        if days < 0:
            health = f"🔴 EXPIRED ({abs(days)} days ago)"
        elif days <= 7:
            health = f"🔴 CRITICAL ({days} days remaining)"
        elif days <= 30:
            health = f"🟡 EXPIRING SOON ({days} days remaining)"
        else:
            health = f"🟢 VALID ({days} days remaining)"

        chain_label = "🟢 Trusted CA Verified" if info["verified_chain"] else (
            f"🟡 Self-Signed" if info["self_signed"] else f"🟡 Unverified ({info['verify_error'][:100]})"
        )
        san_preview = ", ".join(info["sans"][:12]) + (f" (+{len(info['sans']) - 12} more)" if len(info["sans"]) > 12 else "")

        return "\n".join([
            f"### 🔐 SSL/TLS Certificate Audit: `{clean_host}:{target_port}`",
            f"- **Certificate Health:** {health}",
            f"- **Chain Trust:** {chain_label}",
            f"- **TLS Protocol / Cipher:** `{info['tls_version']}` / `{info['cipher']}`",
            f"- **Subject:** `{info['subject']}`",
            f"- **Issuer:** `{info['issuer']}`",
            f"- **Valid From -> Until:** `{info['not_before']}` -> `{info['not_after']}`",
            f"- **SAN Domains/IPs:** `{san_preview or 'None'}`",
            f"- **SHA-256 Fingerprint:** `{info['sha256_fingerprint']}`",
        ])

    # 3. HTTP/HTTPS Endpoint & Security Header Health Check
    @staticmethod
    async def http_endpoint_health_check(
        url: str,
        method: str = "GET",
        expected_status: int = 200,
        timeout_sec: float = 8.0,
        follow_redirects: bool = True,
    ) -> str:
        """Checks HTTP(S) reachability, status code, response latency, redirects, and security headers."""
        target_url = (url or "").strip()
        if not target_url:
            raise ValueError("URL cannot be empty.")
        if not target_url.startswith(("http://", "https://")):
            target_url = f"http://{target_url}"

        verb = (method or "GET").strip().upper()
        if verb not in ("GET", "HEAD", "OPTIONS"):
            raise ValueError("Method must be GET, HEAD, or OPTIONS (read-only safe).")

        timeout = max(1.0, min(20.0, float(timeout_sec)))
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=bool(follow_redirects),
                verify=False,
            ) as client:
                resp = await client.request(verb, target_url)
            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        except Exception as exc:
            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            return "\n".join([
                f"### 🔴 HTTP Endpoint UNREACHABLE: `{target_url}`",
                f"- **Method:** `{verb}` | **Elapsed:** `{latency_ms} ms`",
                f"- **Error:** `{type(exc).__name__}: {exc}`",
            ])

        sec_headers = [
            "strict-transport-security",
            "content-security-policy",
            "x-frame-options",
            "x-content-type-options",
            "referrer-policy",
        ]
        present = [h for h in sec_headers if h in resp.headers]
        missing = [h for h in sec_headers if h not in resp.headers]
        matched = resp.status_code == int(expected_status)
        status_icon = "🟢" if matched or (200 <= resp.status_code < 400) else "🔴"

        lines = [
            f"### {status_icon} HTTP Health Check: `{target_url}`",
            f"- **HTTP Status:** `{resp.status_code}` (Expected `{expected_status}` -> {'PASS' if matched else 'MISMATCH'})",
            f"- **Latency:** `{latency_ms} ms` | **Method:** `{verb}`",
            f"- **Final URL:** `{str(resp.url)}` (Redirects: `{len(resp.history)}`)",
            f"- **Server / Content-Type:** `{resp.headers.get('server', 'Hidden')}` | `{resp.headers.get('content-type', 'Unknown')}`",
            f"- **Payload Size:** `{len(resp.content)} bytes`",
            f"- **Security Headers Present ({len(present)}/5):** `{', '.join(present) if present else 'None'}`",
        ]
        if missing:
            lines.append(f"- **Missing Hardening Headers:** `{', '.join(missing)}`")
        return "\n".join(lines)

    # 4. CIDR & IP Subnet Calculator
    @staticmethod
    def subnet_ip_calculator(cidr: str) -> str:
        """Calculates IPv4/IPv6 network/broadcast address, subnet/wildcard mask, usable range, and scope."""
        raw = (cidr or "").strip()
        if not raw:
            raise ValueError("CIDR string is required (e.g. '192.168.9.0/24').")
        net = ipaddress.ip_network(raw, strict=False)
        is_v4 = isinstance(net, ipaddress.IPv4Network)

        total_ips = net.num_addresses
        if is_v4 and net.prefixlen < 31:
            usable_count = max(0, total_ips - 2)
            first_usable = str(ipaddress.IPv4Address(int(net.network_address) + 1))
            last_usable = str(ipaddress.IPv4Address(int(net.broadcast_address) - 1))
        elif is_v4 and net.prefixlen == 31:
            usable_count = 2
            first_usable = str(net.network_address)
            last_usable = str(net.broadcast_address)
        elif is_v4:
            usable_count = 1
            first_usable = str(net.network_address)
            last_usable = str(net.network_address)
        else:
            usable_count = total_ips
            first_usable = str(net.network_address)
            last_usable = str(net[-1])

        scopes = []
        if net.is_private:
            scopes.append("Private/RFC1918")
        if net.is_global:
            scopes.append("Public/Global")
        if net.is_loopback:
            scopes.append("Loopback")
        if net.is_link_local:
            scopes.append("Link-Local")

        lines = [
            f"### 🧮 IP Subnet Calculation: `{str(net)}` (IPv{net.version})",
            f"- **Network Address:** `{net.network_address}` | **Prefix:** `/{net.prefixlen}`",
            f"- **Subnet Mask:** `{net.netmask}` | **Wildcard Mask:** `{net.hostmask}`",
        ]
        if is_v4:
            lines.append(f"- **Broadcast Address:** `{net.broadcast_address}`")
        lines.extend([
            f"- **Usable Host Range:** `{first_usable}` — `{last_usable}`",
            f"- **Usable Hosts:** `{usable_count:,}` (Total Addresses: `{total_ips:,}`)",
            f"- **Scope / Classification:** `{', '.join(scopes) or 'Standard'}`",
        ])
        return "\n".join(lines)

    # 5. Asynchronous LAN Subnet Discovery Scan
    @staticmethod
    async def lan_subnet_discovery_scan(
        subnet: str = "192.168.9.0/24",
        ports: Optional[List[int]] = None,
        max_hosts: int = 32,
        start_offset: int = 0,
        timeout_sec: float = 0.45,
    ) -> str:
        """Discovers live hosts and open management ports across an IPv4 CIDR slice (up to 64 hosts)."""
        net = ipaddress.ip_network((subnet or "192.168.9.0/24").strip(), strict=False)
        if net.version != 4:
            raise ValueError("LAN discovery scan currently supports IPv4 subnets.")

        hosts = list(net.hosts()) if net.prefixlen < 31 else list(net)
        offset = max(0, int(start_offset))
        limit = max(1, min(64, int(max_hosts)))
        slice_hosts = [str(ip) for ip in hosts[offset : offset + limit]]
        scan_ports = [int(p) for p in (ports or [22, 53, 80, 443, 445, 3389, 3399, 8000, 8080])][:15]
        probe_timeout = max(0.2, min(2.0, float(timeout_sec)))

        sem = asyncio.Semaphore(96)

        async def _probe_port(ip_str: str, port_num: int) -> Optional[Tuple[int, float]]:
            async with sem:
                t0 = time.perf_counter()
                try:
                    conn = asyncio.open_connection(ip_str, port_num)
                    _, writer = await asyncio.wait_for(conn, timeout=probe_timeout)
                    lat = round((time.perf_counter() - t0) * 1000, 1)
                    writer.close()
                    try:
                        await writer.wait_closed()
                    except Exception:
                        pass
                    return (port_num, lat)
                except Exception:
                    return None

        async def _scan_host(ip_str: str) -> Optional[Dict[str, Any]]:
            port_results = await asyncio.gather(*[_probe_port(ip_str, p) for p in scan_ports])
            open_ports = [res for res in port_results if res is not None]
            if not open_ports:
                return None
            hostname = await _reverse_dns(ip_str, timeout_sec=0.5)
            return {"ip": ip_str, "hostname": hostname or "—", "open_ports": open_ports}

        t_scan_start = time.perf_counter()
        scanned = await asyncio.gather(*[_scan_host(ip) for ip in slice_hosts])
        live_hosts = [h for h in scanned if h is not None]
        total_ms = round((time.perf_counter() - t_scan_start) * 1000, 1)

        lines = [
            f"### 📡 LAN Subnet Discovery Scan: `{str(net)}`",
            f"- **Range Scanned:** `{slice_hosts[0] if slice_hosts else 'N/A'}` -> `{slice_hosts[-1] if slice_hosts else 'N/A'}` (`{len(slice_hosts)}` hosts in `{total_ms} ms`)",
            f"- **Ports Probed:** `{', '.join(str(p) for p in scan_ports)}` | **Live Service Hosts:** `{len(live_hosts)}`",
            "",
            "| IP Address | Reverse DNS Hostname | Open Ports & Services |",
            "| :--- | :--- | :--- |",
        ]
        for h in live_hosts:
            p_desc = ", ".join(f"**{p}** ({_COMMON_PORT_LABELS.get(p, 'TCP')} `{lat}ms`)" for p, lat in h["open_ports"])
            lines.append(f"| `{h['ip']}` | `{h['hostname']}` | {p_desc} |")

        if not live_hosts:
            lines.append("| — | — | No responsive hosts found on probed TCP ports in this slice |")

        return "\n".join(lines)

    # 6. Server Top Processes, Listening Ports & Network Interface Audit
    @staticmethod
    async def server_process_and_ports_audit(
        top_n: int = 12,
        sort_by: str = "memory",
        include_connections: bool = True,
    ) -> str:
        """Audits top CPU/RAM processes, listening TCP/UDP sockets, and NIC RX/TX traffic."""
        n_limit = max(1, min(30, int(top_n)))
        sort_key = "cpu" if (sort_by or "").strip().lower() == "cpu" else "memory"

        def _collect() -> Dict[str, Any]:
            import psutil

            # Prime CPU counters briefly
            procs = []
            for p in psutil.process_iter(["pid", "name", "status", "memory_info", "memory_percent", "cpu_percent", "cmdline"]):
                try:
                    info = p.info
                    mem_mb = round((info["memory_info"].rss / (1024 * 1024)) if info.get("memory_info") else 0.0, 1)
                    cmd = " ".join(info.get("cmdline") or [])[:65] or info.get("name", "proc")
                    procs.append({
                        "pid": info["pid"],
                        "name": (info.get("name") or "")[:24],
                        "cpu": round(float(info.get("cpu_percent") or 0.0), 1),
                        "mem_mb": mem_mb,
                        "mem_pct": round(float(info.get("memory_percent") or 0.0), 1),
                        "status": info.get("status", "?"),
                        "cmd": cmd,
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            procs.sort(key=lambda x: x["cpu"] if sort_key == "cpu" else x["mem_mb"], reverse=True)

            listeners: List[Dict[str, Any]] = []
            if include_connections:
                try:
                    for c in psutil.net_connections(kind="inet"):
                        if c.status == "LISTEN" or (c.type == socket.SOCK_DGRAM and c.laddr):
                            listeners.append({
                                "proto": "TCP" if c.type == socket.SOCK_STREAM else "UDP",
                                "addr": f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "-",
                                "pid": c.pid or "-",
                                "service": _COMMON_PORT_LABELS.get(c.laddr.port, "App") if c.laddr else "-",
                            })
                except Exception:
                    pass

            nics = []
            for name, st in psutil.net_io_counters(pernic=True).items():
                if name == "lo" and st.bytes_recv == 0:
                    continue
                nics.append({
                    "iface": name,
                    "rx_mb": round(st.bytes_recv / (1024 * 1024), 2),
                    "tx_mb": round(st.bytes_sent / (1024 * 1024), 2),
                    "errs": st.errin + st.errout,
                    "drops": st.dropin + st.dropout,
                })

            vm = psutil.virtual_memory()
            load1, load5, load15 = os.getloadavg() if hasattr(os, "getloadavg") else (0.0, 0.0, 0.0)
            return {
                "ram_pct": vm.percent,
                "load_avg": f"{load1:.2f}, {load5:.2f}, {load15:.2f}",
                "total_procs": len(procs),
                "top_procs": procs[:n_limit],
                "listeners": listeners[:25],
                "nics": nics[:8],
            }

        snap = await asyncio.to_thread(_collect)
        lines = [
            f"### 🖥️ Server Process, Sockets & Network Interface Audit",
            f"- **Load Avg (1/5/15m):** `{snap['load_avg']}` | **RAM Usage:** `{snap['ram_pct']}%` | **Processes:** `{snap['total_procs']}`",
            "",
            f"**Top {len(snap['top_procs'])} Processes (sorted by {sort_key.upper()}):**",
            "| PID | Name | CPU % | RAM (MB / %) | Command |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]
        for p in snap["top_procs"]:
            lines.append(f"| `{p['pid']}` | `{p['name']}` | `{p['cpu']}%` | `{p['mem_mb']} MB ({p['mem_pct']}%)` | `{p['cmd']}` |")

        if include_connections and snap["listeners"]:
            lines.extend([
                "",
                f"**Active Listening Sockets ({len(snap['listeners'])}):**",
                "| Proto | Listen Address | Service | PID |",
                "| :--- | :--- | :--- | :--- |",
            ])
            for s in snap["listeners"]:
                lines.append(f"| `{s['proto']}` | `{s['addr']}` | {s['service']} | `{s['pid']}` |")

        if snap["nics"]:
            lines.extend(["", "**Network Interfaces RX/TX:**"])
            for nic in snap["nics"]:
                lines.append(
                    f"- `{nic['iface']}`: RX `{nic['rx_mb']} MB` | TX `{nic['tx_mb']} MB` | Err/Drop `{nic['errs']}/{nic['drops']}`"
                )

        return "\n".join(lines)

    # 7. Unified System, Workflow & Security Logs Inspector
    @staticmethod
    async def system_logs_inspector(
        log_source: str = "all",
        keyword: Optional[str] = None,
        level: str = "ALL",
        tail_lines: int = 30,
    ) -> str:
        """Inspects Workflow failures/runs, Security Audit logs, Telegram polling errors, and *.log files."""
        src = (log_source or "all").strip().lower()
        kw = (keyword or "").strip().lower()
        lvl = (level or "ALL").strip().upper()
        limit = max(5, min(100, int(tail_lines)))

        sections: List[str] = [f"### 📋 IT System & Operational Logs Inspector (source=`{src}`, level=`{lvl}`)"]

        def _matches(text: str, entry_level: str = "INFO") -> bool:
            if lvl != "ALL" and lvl not in entry_level.upper() and lvl not in text.upper():
                return False
            if kw and kw not in text.lower():
                return False
            return True

        # A. Workflow execution runs from ops.db
        if src in ("all", "workflows"):
            ops_db = os.path.join(settings.DATA_DIR, "ops.db")
            if os.path.exists(ops_db):
                try:
                    def _read_wf_runs():
                        conn = sqlite3.connect(ops_db)
                        conn.row_factory = sqlite3.Row
                        rows = conn.execute(
                            "SELECT id, workflow_name, status, trigger_source, duration_ms, started_at, error_message "
                            "FROM ops_workflow_runs ORDER BY started_at DESC LIMIT ?",
                            (limit,),
                        ).fetchall()
                        conn.close()
                        return [dict(r) for r in rows]

                    wf_rows = await asyncio.to_thread(_read_wf_runs)
                    matched_wf = [
                        r for r in wf_rows
                        if _matches(f"{r.get('workflow_name')} {r.get('status')} {r.get('error_message')}", str(r.get("status", "")))
                    ]
                    sections.append(f"\n**⚙️ Workflow Runs (`{len(matched_wf)}` shown):**")
                    for r in matched_wf[:15]:
                        err = f" — `{r['error_message'][:120]}`" if r.get("error_message") else ""
                        sections.append(
                            f"- `[{r['status']}]` {r['started_at']} | **{r['workflow_name']}** ({r['trigger_source']}, {r['duration_ms']}ms){err}"
                        )
                except Exception as exc:
                    sections.append(f"- Workflow DB read note: `{exc}`")

        # B. Telegram Bot Config / Polling status
        if src in ("all", "telegram"):
            try:
                from workflows.store import WorkflowStore
                from workflows.telegram_service import telegram_chat_listener
                tg = await WorkflowStore.get_telegram_config()
                lst = telegram_chat_listener.get_runtime_state()
                sections.append("\n**🤖 Telegram Bot Telemetry:**")
                sections.append(
                    f"- Bot: `{tg.get('bot_username') or 'N/A'}` | Enabled: `{tg.get('is_enabled')}` | "
                    f"Polling Active: `{lst.get('polling_active')}` (Running: `{lst.get('listener_running')}`) | "
                    f"Sent: `{tg.get('sent_count', 0)}` | Last Error: `{tg.get('last_error') or 'None'}` | "
                    f"Poll Error: `{lst.get('poll_error') or 'None'}`"
                )
            except Exception as exc:
                sections.append(f"- Telegram status note: `{exc}`")

        # C. Security Audit Database or Log Files
        if src in ("all", "security", "files"):
            audit_db = os.path.join(settings.DATA_DIR, "security_audit.db")
            if os.path.exists(audit_db) and src in ("all", "security"):
                try:
                    def _read_audit():
                        conn = sqlite3.connect(audit_db)
                        conn.row_factory = sqlite3.Row
                        tbls = [r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
                        if not tbls:
                            conn.close()
                            return []
                        rows = conn.execute(f"SELECT * FROM {tbls[0]} ORDER BY rowid DESC LIMIT ?", (limit,)).fetchall()
                        conn.close()
                        return [dict(r) for r in rows]

                    sec_rows = await asyncio.to_thread(_read_audit)
                    matched_sec = [r for r in sec_rows if _matches(json.dumps(r, ensure_ascii=False), str(r.get("severity", "INFO")))]
                    sections.append(f"\n**🛡️ Security Audit Events (`{len(matched_sec)}` matched):**")
                    for r in matched_sec[:12]:
                        sections.append(
                            f"- `[{r.get('severity', 'INFO')}]` {r.get('iso_time', '')} | "
                            f"**{r.get('action', '')}** | user=`{r.get('username', '')}` (`{r.get('resource', '')}`)"
                        )
                except Exception as exc:
                    sections.append(f"- Security audit read note: `{exc}`")

            log_dirs = [settings.DATA_DIR, "/app/logs", "./logs"]
            found_lines: List[str] = []
            for d in log_dirs:
                if not os.path.isdir(d):
                    continue
                for fname in os.listdir(d):
                    if not fname.endswith(".log"):
                        continue
                    fpath = os.path.join(d, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8", errors="replace") as fh:
                            tail = fh.readlines()[-limit:]
                        for line in tail:
                            clean = line.strip()
                            if clean and _matches(clean):
                                found_lines.append(f"[{fname}] {clean[:180]}")
                    except Exception:
                        continue
            if found_lines:
                sections.append(f"\n**📄 Log File Entries (`{len(found_lines[:limit])}`):**")
                for ln in found_lines[-min(15, limit):]:
                    sections.append(f"- `{ln}`")

        return "\n".join(sections)

    # 8. Safe Hop-by-Hop Network Path / Traceroute
    @staticmethod
    async def network_traceroute_or_path(
        target: str,
        max_hops: int = 12,
        timeout_sec: float = 1.5,
    ) -> str:
        """Traces network hops to target IP/domain using TTL probes (iputils-ping) + reverse DNS."""
        clean_target = _clean_host(target)
        hops_limit = max(1, min(25, int(max_hops)))
        per_hop_wait = max(1, min(3, int(round(timeout_sec))))

        loop = asyncio.get_running_loop()
        try:
            resolved_ip = await asyncio.wait_for(
                loop.run_in_executor(None, lambda: socket.gethostbyname(clean_target)),
                timeout=3.0,
            )
        except Exception as exc:
            return f"### 🔴 Traceroute Error: `{clean_target}`\n- Cannot resolve target: `{exc}`"

        async def _probe_ttl(ttl: int) -> Dict[str, Any]:
            t0 = time.perf_counter()
            proc = await asyncio.create_subprocess_exec(
                "ping", "-n", "-c", "1", "-W", str(per_hop_wait), "-t", str(ttl), resolved_ip,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=per_hop_wait + 1.5)
            except asyncio.TimeoutError:
                proc.kill()
                return {"ttl": ttl, "hop_ip": "*", "rtt": "timeout", "reached": False}

            out = stdout.decode("utf-8", errors="replace") + stderr.decode("utf-8", errors="replace")
            elapsed = round((time.perf_counter() - t0) * 1000, 1)

            from_match = re.search(r"From\s+([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+).*?(?:Time to live exceeded|TTL)", out, re.IGNORECASE)
            if from_match:
                return {"ttl": ttl, "hop_ip": from_match.group(1), "rtt": f"{elapsed} ms", "reached": False}

            reply_match = re.search(r"from\s+([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+).*?time=([0-9.]+)\s*ms", out, re.IGNORECASE)
            if reply_match:
                return {"ttl": ttl, "hop_ip": reply_match.group(1), "rtt": f"{reply_match.group(2)} ms", "reached": True}

            return {"ttl": ttl, "hop_ip": "*", "rtt": "timeout", "reached": False}

        hops: List[Dict[str, Any]] = []
        for ttl in range(1, hops_limit + 1):
            hop = await _probe_ttl(ttl)
            if hop["hop_ip"] != "*":
                hop["hostname"] = await _reverse_dns(hop["hop_ip"], timeout_sec=0.4)
            else:
                hop["hostname"] = ""
            hops.append(hop)
            if hop["reached"]:
                break

        lines = [
            f"### 🛣️ Network Path & TTL Hop Trace: `{clean_target}` (`{resolved_ip}`)",
            "| Hop | Router / IP Address | Hostname | Latency / Status |",
            "| :--- | :--- | :--- | :--- |",
        ]
        for h in hops:
            status = f"🟢 {h['rtt']} (Reached)" if h["reached"] else (f"🟡 * ({h['rtt']})" if h["hop_ip"] == "*" else f"🔹 {h['rtt']}")
            lines.append(f"| `{h['ttl']}` | `{h['hop_ip']}` | `{h.get('hostname') or '—'}` | {status} |")

        return "\n".join(lines)

    # 9. IT Security Swiss-Army Utility (Passwords, Tokens, Hashes, JWT Decode)
    @staticmethod
    def it_security_utility(
        action: str = "generate_password",
        value: Optional[str] = None,
        length: int = 20,
        hash_alg: str = "sha256",
    ) -> str:
        """Pure-Python security toolkit: generate strong passwords/tokens, hash checksums, audit strength, or decode JWT."""
        act = (action or "generate_password").strip().lower()
        key_len = max(8, min(128, int(length)))

        if act == "generate_password":
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
            # Guarantee at least one character from each class
            chars = [
                secrets.choice(string.ascii_uppercase),
                secrets.choice(string.ascii_lowercase),
                secrets.choice(string.digits),
                secrets.choice("!@#$%^&*()-_=+"),
            ] + [secrets.choice(alphabet) for _ in range(key_len - 4)]
            secrets.SystemRandom().shuffle(chars)
            pw = "".join(chars)
            entropy = round(key_len * math.log2(len(alphabet)), 1)
            return "\n".join([
                "### 🔑 Generated Enterprise Password",
                f"- **Password:** `{pw}`",
                f"- **Length:** `{key_len}` chars | **Estimated Entropy:** `{entropy} bits` (🟢 Strong)",
            ])

        if act == "generate_api_token":
            token_url = secrets.token_urlsafe(key_len)
            token_hex = secrets.token_hex(key_len)
            return "\n".join([
                "### 🔐 Generated Cryptographic API / Secret Keys",
                f"- **URL-Safe Base64 Token:** `{token_url}`",
                f"- **Hex Secret ({len(token_hex)} hex chars):** `{token_hex}`",
            ])

        if act == "hash_text":
            raw = value or ""
            if not raw:
                raise ValueError("'value' is required for hash_text action.")
            alg = (hash_alg or "sha256").strip().lower()
            if alg not in ("md5", "sha1", "sha256", "sha512"):
                raise ValueError("Supported hash_alg values: md5, sha1, sha256, sha512.")
            digest = getattr(hashlib, alg)(raw.encode("utf-8")).hexdigest()
            return "\n".join([
                f"### #️⃣ {alg.upper()} Digest",
                f"- **Hex Digest:** `{digest}`",
                f"- **Input Length:** `{len(raw)}` bytes",
            ])

        if act == "check_password_strength":
            raw = value or ""
            if not raw:
                raise ValueError("'value' is required for check_password_strength action.")
            classes = {
                "uppercase": any(c.isupper() for c in raw),
                "lowercase": any(c.islower() for c in raw),
                "digits": any(c.isdigit() for c in raw),
                "symbols": any(not c.isalnum() for c in raw),
            }
            pool = (26 if classes["uppercase"] else 0) + (26 if classes["lowercase"] else 0) + (10 if classes["digits"] else 0) + (32 if classes["symbols"] else 0)
            entropy = round(len(raw) * math.log2(max(pool, 1)), 1)
            score = sum(classes.values()) + (2 if len(raw) >= 12 else (1 if len(raw) >= 8 else 0))
            verdict = "🟢 Strong" if score >= 5 and entropy >= 60 else ("🟡 Moderate" if score >= 3 else "🔴 Weak")
            masked = (raw[:2] + "*" * max(2, len(raw) - 4) + raw[-2:]) if len(raw) > 4 else "*" * len(raw)
            return "\n".join([
                f"### 🛡️ Password Strength Audit (`{masked}`)",
                f"- **Verdict:** {verdict} (`{entropy} bits` entropy, `{len(raw)}` chars)",
                f"- **Character Classes:** Upper=`{classes['uppercase']}`, Lower=`{classes['lowercase']}`, Digit=`{classes['digits']}`, Symbol=`{classes['symbols']}`",
            ])

        if act == "inspect_jwt":
            raw_jwt = (value or "").strip()
            parts = raw_jwt.split(".")
            if len(parts) != 3:
                raise ValueError("Invalid JWT format: expected 3 dot-separated segments.")

            def _b64_decode(seg: str) -> Dict[str, Any]:
                padded = seg + "=" * ((4 - len(seg) % 4) % 4)
                return json.loads(base64.urlsafe_b64decode(padded.encode("utf-8")).decode("utf-8"))

            hdr = _b64_decode(parts[0])
            payload = _b64_decode(parts[1])
            exp_note = "No `exp` claim"
            if isinstance(payload.get("exp"), (int, float)):
                exp_dt = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
                is_exp = exp_dt < datetime.now(timezone.utc)
                exp_note = f"`{exp_dt.strftime('%Y-%m-%d %H:%M UTC')}` ({'🔴 EXPIRED' if is_exp else '🟢 ACTIVE'})"

            return "\n".join([
                "### 🪪 JWT Token Inspection (Read-Only Decode)",
                f"- **Algorithm:** `{hdr.get('alg', '?')}` | **Expiry:** {exp_note}",
                f"- **Header:**\n```json\n{json.dumps(hdr, indent=2)}\n```",
                f"- **Payload:**\n```json\n{json.dumps(payload, indent=2, ensure_ascii=False)}\n```",
            ])

        raise ValueError(
            f"Unsupported action '{action}'. Use: generate_password, generate_api_token, hash_text, check_password_strength, inspect_jwt."
        )

    # 10. Cron Schedule Validator & Maintenance Window Planner
    @staticmethod
    def cron_schedule_and_maintenance_planner(
        expression: str,
        count: int = 5,
    ) -> str:
        """Validates a 5-field cron expression/alias, explains it in EN+BN, and previews next N Asia/Dhaka runs."""
        from cron.cron_parser import CronExpression

        runs_count = max(1, min(20, int(count)))
        cron = CronExpression(expression)
        dhaka_tz = timezone(timedelta(hours=6))
        now_dhaka = datetime.now(dhaka_tz).replace(tzinfo=None)
        upcoming = cron.get_next_runs(count=runs_count, base_time=now_dhaka)

        lines = [
            f"### ⏱️ Cron Schedule & Maintenance Window Plan",
            f"- **Expression:** `{cron.expression}` (Raw: `{cron.raw_expression}`)",
            f"- **English:** {cron.to_human_en()}",
            f"- **বাংলা:** {cron.to_human_bn()}",
            f"- **Timezone:** `Asia/Dhaka (UTC+6)`",
            "",
            f"**Next {len(upcoming)} Scheduled Executions:**",
        ]
        for idx, dt in enumerate(upcoming, 1):
            lines.append(f"{idx}. `{dt.strftime('%Y-%m-%d %H:%M:%S')} ({dt.strftime('%A')})`")
        return "\n".join(lines)

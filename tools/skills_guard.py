#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Skills Guard - 技能安全扫描模块

提供 Prompt 注入检测、可疑命令识别、网络请求检测、文件访问检测、环境变量泄露检测等安全功能。

信任级别:
    - builtin:   内置技能，从不扫描，始终信任
    - trusted:   官方可信技能源，允许 caution 判定
    - community: 社区技能，任何发现都阻止
    - agent-created: Agent 创建的技能，危险判定时询问

判定结果:
    - allow:  允许安装
    - block:  阻止安装
    - ask:    需要用户确认

Usage:
    from tools.skills_guard import scan_skill, should_allow_install, format_scan_report

    result = scan_skill(Path("skills/my-skill"), source="community")
    allowed, reason = should_allow_install(result)
    if not allowed:
        print(format_scan_report(result))
"""

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

# =============================================================================
# 信任配置
# =============================================================================

TRUSTED_REPOS = {"openai/skills", "anthropic/skills", "huggingface/skills"}

# 策略: (safe判定结果, caution判定结果, dangerous判定结果)
INSTALL_POLICY = {
    "builtin": ("allow", "allow", "allow"),
    "trusted": ("allow", "allow", "block"),
    "community": ("allow", "block", "block"),
    "agent-created": ("allow", "allow", "ask"),
}

VERDICT_INDEX = {"safe": 0, "caution": 1, "dangerous": 2}


# =============================================================================
# 数据结构
# =============================================================================

@dataclass
class Finding:
    """安全扫描发现项"""
    pattern_id: str
    severity: str  # "critical" | "high" | "medium" | "low"
    category: str  # "exfiltration" | "injection" | "destructive" | "persistence" | "network" | "obfuscation"
    file: str
    line: int
    match: str
    description: str


@dataclass
class ScanResult:
    """扫描结果"""
    skill_name: str
    source: str
    trust_level: str  # "builtin" | "trusted" | "community" | "agent-created"
    verdict: str  # "safe" | "caution" | "dangerous"
    findings: List[Finding] = field(default_factory=list)
    scanned_at: str = ""
    summary: str = ""


# =============================================================================
# 危险模式列表
# =============================================================================

THREAT_PATTERNS = [
    # ── 环境变量泄露: shell 命令 ──
    (r"curl\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|API)",
     "env_exfil_curl", "critical", "exfiltration",
     "curl 命令包含敏感环境变量"),
    (r"wget\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|API)",
     "env_exfil_wget", "critical", "exfiltration",
     "wget 命令包含敏感环境变量"),
    (r"fetch\s*\([^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD|API)",
     "env_exfil_fetch", "critical", "exfiltration",
     "fetch() 调用包含敏感环境变量"),
    (r"requests\.(get|post|put|patch)\s*\([^\n]*(KEY|TOKEN|SECRET|PASSWORD)",
     "env_exfil_requests", "critical", "exfiltration",
     "requests 库调用包含敏感变量"),

    # ── 环境变量泄露: 凭据存储 ──
    (r"\$HOME/\.ssh|\~/\.ssh",
     "ssh_dir_access", "high", "exfiltration",
     "访问用户 SSH 目录"),
    (r"\$HOME/\.aws|\~/\.aws",
     "aws_dir_access", "high", "exfiltration",
     "访问 AWS 凭据目录"),
    (r"\$HOME/\.gnupg|\~/\.gnupg",
     "gpg_dir_access", "high", "exfiltration",
     "访问 GPG 密钥环"),
    (r"\$HOME/\.kube|\~/\.kube",
     "kube_dir_access", "high", "exfiltration",
     "访问 Kubernetes 配置目录"),
    (r"\$HOME/\.docker|\~/\.docker",
     "docker_dir_access", "high", "exfiltration",
     "访问 Docker 配置"),
    (r"cat\s+[^\n]*(\.env|credentials|\.netrc|\.pgpass|\.npmrc|\.pypirc)",
     "read_secrets_file", "critical", "exfiltration",
     "读取已知凭据文件"),

    # ── 环境变量泄露: 程序化访问 ──
    (r"printenv|env\s*\|",
     "dump_all_env", "high", "exfiltration",
     "转储所有环境变量"),
    (r"os\.environ\b(?!\s*\.get\s*\(\s*[\"']PATH)",
     "python_os_environ", "high", "exfiltration",
     "访问 os.environ (潜在环境变量泄露)"),
    (r"os\.getenv\s*\(\s*[^\)]*(?:KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)",
     "python_getenv_secret", "critical", "exfiltration",
     "通过 os.getenv() 读取敏感凭据"),
    (r"process\.env\[",
     "node_process_env", "high", "exfiltration",
     "访问 process.env (Node.js 环境)"),

    # ── Prompt 注入 ──
    (r"ignore\s+(?:\w+\s+)*(previous|all|above|prior)\s+instructions",
     "prompt_injection_ignore", "critical", "injection",
     "Prompt 注入: 忽略之前的指令"),
    (r"you\s+are\s+(?:\w+\s+)*now\s+",
     "role_hijack", "high", "injection",
     "尝试覆盖 Agent 角色"),
    (r"do\s+not\s+(?:\w+\s+)*tell\s+(?:\w+\s+)*the\s+user",
     "deception_hide", "critical", "injection",
     "指示 Agent 向用户隐瞒信息"),
    (r"system\s+prompt\s+override",
     "sys_prompt_override", "critical", "injection",
     "尝试覆盖系统 Prompt"),
    (r"pretend\s+(?:\w+\s+)*(you\s+are|to\s+be)\s+",
     "role_pretend", "high", "injection",
     "尝试让 Agent 扮演其他身份"),
    (r"disregard\s+(?:\w+\s+)*(your|all|any)\s+(?:\w+\s+)*(instructions|rules|guidelines)",
     "disregard_rules", "critical", "injection",
     "指示 Agent 忽略其规则"),
    (r"output\s+(?:\w+\s+)*(system|initial)\s+prompt",
     "leak_system_prompt", "high", "injection",
     "尝试提取系统 Prompt"),
    (r"(when|if)\s+no\s+one\s+is\s+(watching|looking)",
     "conditional_deception", "high", "injection",
     "条件指令: 无监督时行为不同"),
    (r"act\s+as\s+(if|though)\s+(?:\w+\s+)*you\s+(?:\w+\s+)*(have\s+no|don't\s+have)\s+(?:\w+\s+)*(restrictions|limits|rules)",
     "bypass_restrictions", "critical", "injection",
     "指示 Agent 无限制行动"),

    # ── 破坏性操作 ──
    (r"rm\s+-rf\s+/",
     "destructive_root_rm", "critical", "destructive",
     "从根目录递归删除"),
    (r"rm\s+(-[^\s]*)?r.*\$HOME|\brmdir\s+.*\$HOME",
     "destructive_home_rm", "critical", "destructive",
     "递归删除主目录"),
    (r"chmod\s+777",
     "insecure_perms", "medium", "destructive",
     "设置全局可写权限"),
    (r">\s*/etc/",
     "system_overwrite", "critical", "destructive",
     "覆盖系统配置文件"),
    (r"\bmkfs\b",
     "format_filesystem", "critical", "destructive",
     "格式化文件系统"),
    (r"\bdd\s+.*if=.*of=/dev/",
     "disk_overwrite", "critical", "destructive",
     "原始磁盘写入操作"),
    (r"shutil\.rmtree\s*\(\s*[\"\'/]",
     "python_rmtree", "high", "destructive",
     "Python rmtree 操作绝对路径"),

    # ── 持久化 ──
    (r"\bcrontab\b",
     "persistence_cron", "medium", "persistence",
     "修改 cron 任务"),
    (r"\.(bashrc|zshrc|profile|bash_profile|bash_login|zprofile|zlogin)\b",
     "shell_rc_mod", "medium", "persistence",
     "引用 shell 启动文件"),
    (r"authorized_keys",
     "ssh_backdoor", "critical", "persistence",
     "修改 SSH 授权密钥"),
    (r"ssh-keygen",
     "ssh_keygen", "medium", "persistence",
     "生成 SSH 密钥"),
    (r"systemd.*\.service|systemctl\s+(enable|start)",
     "systemd_service", "medium", "persistence",
     "引用或启用 systemd 服务"),
    (r"/etc/sudoers|visudo",
     "sudoers_mod", "critical", "persistence",
     "修改 sudoers (权限提升)"),

    # ── 网络: 反向 shell 和隧道 ──
    (r"\bnc\s+-[lp]|ncat\s+-[lp]|\bsocat\b",
     "reverse_shell", "critical", "network",
     "潜在反向 shell 监听器"),
    (r"\bngrok\b|\blocaltunnel\b|\bserveo\b|\bcloudflared\b",
     "tunnel_service", "high", "network",
     "使用隧道服务进行外部访问"),
    (r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{2,5}",
     "hardcoded_ip_port", "medium", "network",
     "硬编码 IP 地址和端口"),
    (r"0\.0\.0\.0:\d+|INADDR_ANY",
     "bind_all_interfaces", "high", "network",
     "绑定到所有网络接口"),
    (r"/bin/(ba)?sh\s+-i\s+.*>/dev/tcp/",
     "bash_reverse_shell", "critical", "network",
     "bash 交互式反向 shell"),
    (r"python[23]?\s+-c\s+[\"']import\s+socket",
     "python_socket_oneliner", "critical", "network",
     "Python 单行 socket 连接 (疑似反向 shell)"),
    (r"webhook\.site|requestbin\.com|pipedream\.net|hookbin\.com",
     "exfil_service", "high", "network",
     "引用已知数据泄露/webhook 测试服务"),

    # ── 混淆: 编码和执行 ──
    (r"base64\s+(-d|--decode)\s*\|",
     "base64_decode_pipe", "high", "obfuscation",
     "base64 解码并管道执行"),
    (r"\\x[0-9a-fA-F]{2}.*\\x[0-9a-fA-F]{2}.*\\x[0-9a-fA-F]{2}",
     "hex_encoded_string", "medium", "obfuscation",
     "十六进制编码字符串 (疑似混淆)"),
    (r"\beval\s*\(\s*[\"']",
     "eval_string", "high", "obfuscation",
     "eval() 使用字符串参数"),
    (r"\bexec\s*\(\s*[\"']",
     "exec_string", "high", "obfuscation",
     "exec() 使用字符串参数"),
    (r"echo\s+[^\n]*\|\s*(bash|sh|python|perl|ruby|node)",
     "echo_pipe_exec", "critical", "obfuscation",
     "echo 管道到解释器执行"),
    (r"getattr\s*\(\s*__builtins__",
     "python_getattr_builtins", "high", "obfuscation",
     "动态访问 Python builtins (绕过技术)"),
    (r"__import__\s*\(\s*[\"']os[\"']\s*\)",
     "python_import_os", "high", "obfuscation",
     "动态导入 os 模块"),

    # ── 进程执行 ──
    (r"subprocess\.(run|call|Popen|check_output)\s*\(",
     "python_subprocess", "medium", "execution",
     "Python subprocess 执行"),
    (r"os\.system\s*\(",
     "python_os_system", "high", "execution",
     "os.system() — 无防护的 shell 执行"),
    (r"os\.popen\s*\(",
     "python_os_popen", "high", "execution",
     "os.popen() — shell 管道执行"),
    (r"child_process\.(exec|spawn|fork)\s*\(",
     "node_child_process", "high", "execution",
     "Node.js child_process 执行"),

    # ── 路径遍历 ──
    (r"\.\./\.\./\.\.",
     "path_traversal_deep", "high", "traversal",
     "深层相对路径遍历 (3+ 级)"),
    (r"\.\./\.\.",
     "path_traversal", "medium", "traversal",
     "相对路径遍历 (2+ 级)"),
    (r"/etc/passwd|/etc/shadow",
     "system_passwd_access", "critical", "traversal",
     "访问系统密码文件"),

    # ── 供应链: curl/wget 管道到 shell ──
    (r"curl\s+[^\n]*\|\s*(ba)?sh",
     "curl_pipe_shell", "critical", "supply_chain",
     "curl 管道到 shell (下载并执行)"),
    (r"wget\s+[^\n]*-O\s*-\s*\|\s*(ba)?sh",
     "wget_pipe_shell", "critical", "supply_chain",
     "wget 管道到 shell (下载并执行)"),
    (r"curl\s+[^\n]*\|\s*python",
     "curl_pipe_python", "critical", "supply_chain",
     "curl 管道到 Python 解释器"),

    # ── 供应链: 未固定版本依赖 ──
    (r"pip\s+install\s+(?!-r\s)(?!.*==)",
     "unpinned_pip_install", "medium", "supply_chain",
     "pip install 未固定版本"),
    (r"npm\s+install\s+(?!.*@\d)",
     "unpinned_npm_install", "medium", "supply_chain",
     "npm install 未固定版本"),

    # ── 供应链: 远程资源获取 ──
    (r"(curl|wget|httpx?\.get|requests\.get|fetch)\s*[\(]?\s*[\"']https?://",
     "remote_fetch", "medium", "supply_chain",
     "运行时获取远程资源"),
    (r"git\s+clone\s+",
     "git_clone", "medium", "supply_chain",
     "运行时克隆 git 仓库"),
    (r"docker\s+pull\s+",
     "docker_pull", "medium", "supply_chain",
     "运行时拉取 Docker 镜像"),

    # ── 权限提升 ──
    (r"\bsudo\b",
     "sudo_usage", "high", "privilege_escalation",
     "使用 sudo (权限提升)"),
    (r"setuid|setgid|cap_setuid",
     "setuid_setgid", "critical", "privilege_escalation",
     "setuid/setgid (权限提升机制)"),
    (r"NOPASSWD",
     "nopasswd_sudo", "critical", "privilege_escalation",
     "NOPASSWD sudoers 条目 (无密码权限提升)"),
    (r"chmod\s+[u+]?s",
     "suid_bit", "critical", "privilege_escalation",
     "设置 SUID/SGID 位"),

    # ── Agent 配置持久化 ──
    (r"AGENTS\.md|CLAUDE\.md|\.cursorrules|\.clinerules",
     "agent_config_mod", "critical", "persistence",
     "引用 agent 配置文件 (可能在会话间持久化恶意指令)"),

    # ── 硬编码凭据 ──
    (r"(?:api[_-]?key|token|secret|password)\s*[=:]\s*[\"'][A-Za-z0-9+/=_-]{20,}",
     "hardcoded_secret", "critical", "credential_exposure",
     "可能的硬编码 API 密钥或令牌"),
    (r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----",
     "embedded_private_key", "critical", "credential_exposure",
     "嵌入的私钥"),
    (r"ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{80,}",
     "github_token_leaked", "critical", "credential_exposure",
     "GitHub 个人访问令牌泄露"),
    (r"sk-[A-Za-z0-9]{20,}",
     "openai_key_leaked", "critical", "credential_exposure",
     "可能的 OpenAI API 密钥泄露"),
    (r"sk-ant-[A-Za-z0-9_-]{90,}",
     "anthropic_key_leaked", "critical", "credential_exposure",
     "可能的 Anthropic API 密钥泄露"),
    (r"AKIA[0-9A-Z]{16}",
     "aws_access_key_leaked", "critical", "credential_exposure",
     "AWS 访问密钥 ID 泄露"),

    # ── 越狱模式 ──
    (r"\bDAN\s+mode\b|Do\s+Anything\s+Now",
     "jailbreak_dan", "critical", "injection",
     "DAN (Do Anything Now) 越狱尝试"),
    (r"\bdeveloper\s+mode\b.*\benabled?\b",
     "jailbreak_dev_mode", "critical", "injection",
     "开发者模式越狱尝试"),
    (r"for\s+educational\s+purposes?\s+only",
     "educational_pretext", "medium", "injection",
     "教育目的借口 (常用于正当化有害内容)"),
    (r"(respond|answer|reply)\s+without\s+(?:\w+\s+)*(restrictions|limitations|filters|safety)",
     "remove_filters", "critical", "injection",
     "指示 Agent 无安全过滤器响应"),
]

# Prompt 注入检测模式列表 (简化版，用于快速检测)
INJECTION_PATTERNS: List[str] = [
    "ignore previous instructions",
    "ignore all previous",
    "you are now",
    "disregard your",
    "forget your instructions",
    "new instructions:",
    "system prompt:",
    "<system>",
    "]]>",
    "```system",
    "END SYSTEM",
    "ignore prior",
    "disregard all",
    "role play:",
    "pretend you are",
    "act as if",
]

# 可扫描的文件扩展名
SCANNABLE_EXTENSIONS = {
    ".md", ".txt", ".py", ".sh", ".bash", ".js", ".ts", ".rb",
    ".yaml", ".yml", ".json", ".toml", ".cfg", ".ini", ".conf",
    ".html", ".css", ".xml", ".tex",
}

# 已知二进制扩展名
SUSPICIOUS_BINARY_EXTENSIONS = {
    ".exe", ".dll", ".so", ".dylib", ".bin", ".dat", ".com",
    ".msi", ".dmg", ".app", ".deb", ".rpm",
}

# 不可见 Unicode 字符
INVISIBLE_CHARS = {
    "\u200b",  # 零宽空格
    "\u200c",  # 零宽非连接符
    "\u200d",  # 零宽连接符
    "\u2060",  # 词连接符
    "\u2062",  # 不可见乘号
    "\u2063",  # 不可见分隔符
    "\u2064",  # 不可见加号
    "\ufeff",  # 零宽不断行空格 (BOM)
    "\u202a",  # 左到右嵌入
    "\u202b",  # 右到左嵌入
    "\u202c",  # 弹出方向格式
    "\u202d",  # 左到右覆盖
    "\u202e",  # 右到左覆盖
}

# 结构限制
MAX_FILE_COUNT = 50
MAX_TOTAL_SIZE_KB = 1024
MAX_SINGLE_FILE_KB = 256


# =============================================================================
# 扫描函数
# =============================================================================

def scan_file(file_path: Path, rel_path: str = "") -> List[Finding]:
    """
    扫描单个文件的安全威胁模式和不可见 Unicode 字符。

    Args:
        file_path: 文件的绝对路径
        rel_path: 相对路径 (用于显示，默认使用文件名)

    Returns:
        发现列表 (按模式和行去重)
    """
    if not rel_path:
        rel_path = file_path.name

    if file_path.suffix.lower() not in SCANNABLE_EXTENSIONS and file_path.name != "SKILL.md":
        return []

    try:
        content = file_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []

    findings = []
    lines = content.split("\n")
    seen: set = set()  # (pattern_id, line_number) 用于去重

    # 正则模式匹配
    for pattern, pid, severity, category, description in THREAT_PATTERNS:
        for i, line in enumerate(lines, start=1):
            if (pid, i) in seen:
                continue
            if re.search(pattern, line, re.IGNORECASE):
                seen.add((pid, i))
                matched_text = line.strip()
                if len(matched_text) > 120:
                    matched_text = matched_text[:117] + "..."
                findings.append(Finding(
                    pattern_id=pid,
                    severity=severity,
                    category=category,
                    file=rel_path,
                    line=i,
                    match=matched_text,
                    description=description,
                ))

    # 不可见 Unicode 字符检测
    for i, line in enumerate(lines, start=1):
        for char in INVISIBLE_CHARS:
            if char in line:
                char_name = _unicode_char_name(char)
                findings.append(Finding(
                    pattern_id="invisible_unicode",
                    severity="high",
                    category="injection",
                    file=rel_path,
                    line=i,
                    match=f"U+{ord(char):04X} ({char_name})",
                    description=f"不可见 Unicode 字符 {char_name} (疑似文本隐藏/注入)",
                ))
                break  # 不可见字符每个发现一行

    return findings


def scan_skill(skill_dir: Path, source: str = "community", enable_ast_audit: bool = False) -> ScanResult:
    """
    扫描技能目录中的所有安全威胁。

    执行:
    1. 结构检查 (文件数量、总大小、二进制文件、符号链接)
    2. 所有文本文件的正则模式匹配
    3. 不可见 Unicode 字符检测
    4. AST 深度审计 (可选，通过 enable_ast_audit 参数启用)

    Args:
        skill_dir: 技能目录路径
        source: 源标识符 (例如 "openai/skills")
        enable_ast_audit: 是否启用 AST 深度审计（检测动态导入/属性访问）

    Returns:
        包含判定、发现和信任元数据的 ScanResult
    """
    skill_name = skill_dir.name
    trust_level = _resolve_trust_level(source)

    all_findings: List[Finding] = []

    if skill_dir.is_dir():
        # 先执行结构检查
        all_findings.extend(_check_structure(skill_dir))

        # 扫描每个文件
        for f in skill_dir.rglob("*"):
            if f.is_file():
                rel = str(f.relative_to(skill_dir))
                all_findings.extend(scan_file(f, rel))

                # AST 深度审计（可选）
                if enable_ast_audit and f.suffix == ".py":
                    all_findings.extend(_scan_python_ast(f, rel))
    elif skill_dir.is_file():
        all_findings.extend(scan_file(skill_dir, skill_dir.name))

        # AST 深度审计（可选）
        if enable_ast_audit and skill_dir.suffix == ".py":
            all_findings.extend(_scan_python_ast(skill_dir, skill_dir.name))

    verdict = _determine_verdict(all_findings)
    summary = _build_summary(skill_name, source, trust_level, verdict, all_findings)

    return ScanResult(
        skill_name=skill_name,
        source=source,
        trust_level=trust_level,
        verdict=verdict,
        findings=all_findings,
        scanned_at=datetime.now(timezone.utc).isoformat(),
        summary=summary,
    )


def _scan_python_ast(file_path: Path, rel_path: str) -> List[Finding]:
    """
    使用 AST 对 Python 文件进行深度审计。

    检测危险模式：
    - importlib.import_module() 动态导入
    - __import__() 带非字面量参数
    - getattr() 带非字面量属性名
    - __dict__[] 动态属性访问

    Args:
        file_path: Python 文件路径
        rel_path: 相对路径（用于报告）

    Returns:
        发现列表
    """
    from tools.skills_ast_audit import scan_skill_directory, _IGNORED_DIRS

    findings = []
    try:
        content = file_path.read_text(encoding="utf-8")
        from tools.skills_ast_audit import _scan_source
        ast_findings = _scan_source(content, rel_path)

        # 转换 AST 审计发现为安全扫描发现
        for file_rel, line_no, pattern_id, description in ast_findings:
            # 截取匹配的代码片段
            lines = content.split("\n")
            match = lines[line_no - 1].strip() if line_no <= len(lines) else ""

            findings.append(Finding(
                pattern_id=f"ast_{pattern_id}",
                severity="medium",  # AST 发现通常是中等严重性
                category="obfuscation",
                file=rel_path,
                line=line_no,
                match=match[:100],
                description=description,
            ))
    except Exception:
        pass  # 无法解析的文件跳过

    return findings


def should_allow_install(result: ScanResult, force: bool = False) -> Tuple[bool | None, str]:
    """
    根据扫描结果和信任级别判断技能是否应被安装。

    Args:
        result: scan_skill() 的扫描结果
        force: 如果为 True，覆盖此扫描结果的阻止策略决策

    Returns:
        (allowed, reason) 元组
            - allowed=True: 允许安装
            - allowed=False: 阻止安装
            - allowed=None: 需要用户确认
    """
    policy = INSTALL_POLICY.get(result.trust_level, INSTALL_POLICY["community"])
    vi = VERDICT_INDEX.get(result.verdict, 2)
    decision = policy[vi]

    if decision == "allow":
        return True, f"允许 ({result.trust_level} 来源, {result.verdict} 判定)"

    if force and not (result.verdict == "dangerous" and result.trust_level in ("community", "trusted")):
        return True, (
            f"强制安装，尽管 {result.verdict} 判定 "
            f"({len(result.findings)} 项发现)"
        )

    if decision == "ask":
        # 返回 None 表示需要用户确认
        return None, (
            f"需要确认 ({result.trust_level} 来源 + {result.verdict} 判定, "
            f"{len(result.findings)} 项发现)"
        )

    # dangerous 判定不能被 --force 覆盖 (community/trusted)
    if result.verdict == "dangerous" and result.trust_level in ("community", "trusted"):
        return False, (
            f"阻止 ({result.trust_level} 来源 + dangerous 判定, "
            f"{len(result.findings)} 项发现)。--force 不会覆盖 dangerous 判定。"
        )
    return False, (
        f"阻止 ({result.trust_level} 来源 + {result.verdict} 判定, "
        f"{len(result.findings)} 项发现)。使用 --force 覆盖。"
    )


def format_scan_report(result: ScanResult) -> str:
    """
    将扫描结果格式化为人类可读的文本报告。

    Args:
        result: scan_skill() 的扫描结果

    Returns:
        适合 CLI 或聊天显示的多行报告
    """
    lines = []

    verdict_display = result.verdict.upper()
    lines.append(f"扫描: {result.skill_name} ({result.source}/{result.trust_level})  判定: {verdict_display}")

    if result.findings:
        # 按严重程度分组和排序: critical 优先，然后 high, medium, low
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_findings = sorted(result.findings, key=lambda f: severity_order.get(f.severity, 4))

        for f in sorted_findings:
            sev = f.severity.upper().ljust(8)
            cat = f.category.ljust(14)
            loc = f"{f.file}:{f.line}".ljust(30)
            lines.append(f"  {sev} {cat} {loc} \"{f.match[:60]}\"")

        lines.append("")

    allowed, reason = should_allow_install(result)
    if allowed is True:
        status = "允许"
    elif allowed is None:
        status = "需要确认"
    else:
        status = "阻止"
    lines.append(f"决策: {status} — {reason}")

    return "\n".join(lines)


def detect_prompt_injection(content: str) -> Tuple[bool, List[str]]:
    """
    检测潜在的 Prompt 注入攻击。

    Args:
        content: 待检测的内容

    Returns:
        (是否检测到注入, 检测到的模式列表)
    """
    content_lower = content.lower()
    detected = []

    for pattern in INJECTION_PATTERNS:
        if pattern.lower() in content_lower:
            detected.append(pattern)

    return len(detected) > 0, detected


def content_hash(skill_dir: Path) -> str:
    """
    计算技能目录中所有文件的 SHA-256 哈希值用于完整性追踪。

    文件路径 (相对于 skill_dir) 与文件内容一起混入哈希，
    这样技能中两个文件交换内容会改变哈希值。
    """
    h = hashlib.sha256()
    if skill_dir.is_dir():
        for f in sorted(skill_dir.rglob("*")):
            if f.is_file():
                try:
                    rel = f.relative_to(skill_dir).as_posix()
                    h.update(rel.encode("utf-8"))
                    h.update(b"\x00")
                    h.update(f.read_bytes())
                except OSError:
                    continue
    elif skill_dir.is_file():
        h.update(skill_dir.read_bytes())
    return f"sha256:{h.hexdigest()[:16]}"


# =============================================================================
# 结构检查
# =============================================================================

def _check_structure(skill_dir: Path) -> List[Finding]:
    """
    检查技能目录的结构异常:
    - 文件过多
    - 总大小可疑
    - 二进制/可执行文件
    - 指向技能目录外的符号链接
    - 单个文件过大
    """
    findings = []
    file_count = 0
    total_size = 0

    for f in skill_dir.rglob("*"):
        if not f.is_file() and not f.is_symlink():
            continue

        rel = str(f.relative_to(skill_dir))
        file_count += 1

        # 符号链接检查
        if f.is_symlink():
            try:
                resolved = f.resolve()
                if not resolved.is_relative_to(skill_dir.resolve()):
                    findings.append(Finding(
                        pattern_id="symlink_escape",
                        severity="critical",
                        category="traversal",
                        file=rel,
                        line=0,
                        match=f"symlink -> {resolved}",
                        description="符号链接指向技能目录外",
                    ))
            except OSError:
                findings.append(Finding(
                    pattern_id="broken_symlink",
                    severity="medium",
                    category="traversal",
                    file=rel,
                    line=0,
                    match="broken symlink",
                    description="损坏或循环符号链接",
                ))
            continue

        # 大小追踪
        try:
            size = f.stat().st_size
            total_size += size
        except OSError:
            continue

        # 单文件过大
        if size > MAX_SINGLE_FILE_KB * 1024:
            findings.append(Finding(
                pattern_id="oversized_file",
                severity="medium",
                category="structural",
                file=rel,
                line=0,
                match=f"{size // 1024}KB",
                description=f"文件大小 {size // 1024}KB (限制: {MAX_SINGLE_FILE_KB}KB)",
            ))

        # 二进制/可执行文件
        ext = f.suffix.lower()
        if ext in SUSPICIOUS_BINARY_EXTENSIONS:
            findings.append(Finding(
                pattern_id="binary_file",
                severity="critical",
                category="structural",
                file=rel,
                line=0,
                match=f"binary: {ext}",
                description=f"技能中不应包含二进制/可执行文件 ({ext})",
            ))

        # 非脚本文件有可执行权限
        if ext not in {".sh", ".bash", ".py", ".rb"} and f.stat().st_mode & 0o111:
            findings.append(Finding(
                pattern_id="unexpected_executable",
                severity="medium",
                category="structural",
                file=rel,
                line=0,
                match="executable bit set",
                description="文件有可执行权限但不是已识别的脚本类型",
            ))

    # 文件数量限制
    if file_count > MAX_FILE_COUNT:
        findings.append(Finding(
            pattern_id="too_many_files",
            severity="medium",
            category="structural",
            file="(directory)",
            line=0,
            match=f"{file_count} files",
            description=f"技能有 {file_count} 个文件 (限制: {MAX_FILE_COUNT})",
        ))

    # 总大小限制
    if total_size > MAX_TOTAL_SIZE_KB * 1024:
        findings.append(Finding(
            pattern_id="oversized_skill",
            severity="high",
            category="structural",
            file="(directory)",
            line=0,
            match=f"{total_size // 1024}KB total",
            description=f"技能总计 {total_size // 1024}KB (限制: {MAX_TOTAL_SIZE_KB}KB)",
        ))

    return findings


def _unicode_char_name(char: str) -> str:
    """获取不可见 Unicode 字符的可读名称。"""
    names = {
        "\u200b": "zero-width space",
        "\u200c": "zero-width non-joiner",
        "\u200d": "zero-width joiner",
        "\u2060": "word joiner",
        "\u2062": "invisible times",
        "\u2063": "invisible separator",
        "\u2064": "invisible plus",
        "\ufeff": "BOM/zero-width no-break space",
        "\u202a": "LTR embedding",
        "\u202b": "RTL embedding",
        "\u202c": "pop directional",
        "\u202d": "LTR override",
        "\u202e": "RTL override",
    }
    return names.get(char, f"U+{ord(char):04X}")


# =============================================================================
# 内部辅助函数
# =============================================================================

def _resolve_trust_level(source: str) -> str:
    """将源标识符映射到信任级别。"""
    prefix_aliases = (
        "skills-sh/",
        "skills.sh/",
        "skils-sh/",
        "skils.sh/",
    )
    normalized_source = source
    for prefix in prefix_aliases:
        if normalized_source.startswith(prefix):
            normalized_source = normalized_source[len(prefix):]
            break

    # Agent 创建的技能有自己宽容的信任级别
    if normalized_source == "agent-created":
        return "agent-created"
    # 随仓库发布的官方可选技能
    if normalized_source.startswith("official/") or normalized_source == "official":
        return "builtin"
    # 检查源是否匹配任何可信仓库
    for trusted in TRUSTED_REPOS:
        if normalized_source.startswith(trusted) or normalized_source == trusted:
            return "trusted"
    return "community"


def _determine_verdict(findings: List[Finding]) -> str:
    """根据发现列表确定总体判定。"""
    if not findings:
        return "safe"

    has_critical = any(f.severity == "critical" for f in findings)
    has_high = any(f.severity == "high" for f in findings)

    if has_critical:
        return "dangerous"
    if has_high:
        return "caution"
    # 仅 medium/low 发现是信息性的，不阻止
    return "safe"


def _build_summary(
    name: str,
    source: str,
    trust: str,
    verdict: str,
    findings: List[Finding],
) -> str:
    """构建扫描结果的一行摘要。"""
    if not findings:
        return f"{name}: 扫描干净，未检测到威胁"

    categories = {f.category for f in findings}
    return f"{name}: {verdict} — {len(findings)} 项发现 ({', '.join(sorted(categories))})"
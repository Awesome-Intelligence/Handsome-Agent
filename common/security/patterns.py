# Copyright (c) 2026 Agent-Z Contributors
#
# 本项目采用 MIT 许可证开源
# 详细信息请参见 LICENSE 文件

"""
威胁检测模式库
定义所有用于检测恶意代码和安全威胁的正则表达式模式
"""

from typing import List, Tuple

# 提示注入检测模式 - 用于检测尝试覆盖或忽略系统指令的文本
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
]

# 威胁模式元组: (正则表达式, 模式ID, 严重级别, 类别, 描述)
THREAT_PATTERNS: List[Tuple[str, str, str, str, str]] = [
    # ==================== 数据泄露 (Exfiltration) ====================
    # Shell命令泄露密钥
    (
        r'curl\s+[^\n]*\$\{?\w*(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|API)',
        "env_exfil_curl",
        "critical",
        "exfiltration",
        "curl command interpolating secret environment variable",
    ),
    # 访问SSH凭据目录
    (
        r'\$HOME/\.ssh|\~/\.ssh',
        "ssh_dir_access",
        "high",
        "exfiltration",
        "references user SSH directory",
    ),
    # 访问AWS凭据
    (
        r'\$HOME/\.aws|\~/\.aws',
        "aws_dir_access",
        "high",
        "exfiltration",
        "references user AWS credentials directory",
    ),
    # 直接访问Hermes secrets文件
    (
        r'\$HOME/\.Agent-Z/\.env|\~/\.Agent-Z/\.env',
        "agentz_env_access",
        "critical",
        "exfiltration",
        "directly references Agent-Z secrets file",
    ),
    # DNS数据泄露
    (
        r'\b(dig|nslookup|host)\s+[^\n]*\$',
        "dns_exfil",
        "critical",
        "exfiltration",
        "DNS lookup with variable interpolation (possible DNS exfiltration)",
    ),

    # ==================== 提示注入 (Prompt Injection) ====================
    # 忽略之前指令
    (
        r'ignore\s+(?:\w+\s+)*(previous|all|above|prior)\s+instructions',
        "prompt_injection_ignore",
        "critical",
        "injection",
        "prompt injection: ignore previous instructions",
    ),
    # 角色劫持
    (
        r'you\s+are\s+(?:\w+\s+)*now\s+',
        "role_hijack",
        "high",
        "injection",
        "attempts to override the agent's role",
    ),
    # 欺骗性隐藏信息
    (
        r'do\s+not\s+(?:\w+\s+)*tell\s+(?:\w+\s+)*the\s+user',
        "deception_hide",
        "critical",
        "injection",
        "instructs agent to hide information from user",
    ),
    # 系统提示覆盖
    (
        r'system\s+prompt\s+override',
        "sys_prompt_override",
        "critical",
        "injection",
        "attempts to override the system prompt",
    ),
    # DAN越狱模式
    (
        r'\bDAN\s+mode\b|Do\s+Anything\s+Now',
        "jailbreak_dan",
        "critical",
        "injection",
        "DAN (Do Anything Now) jailbreak attempt",
    ),
    # 开发者模式越狱
    (
        r'\bdeveloper\s+mode\b.*\benabled?\b',
        "jailbreak_dev_mode",
        "critical",
        "injection",
        "developer mode jailbreak attempt",
    ),
    # 忽略所有指令的变体
    (
        r'(?:forget|disregard|ignore)\s+everything',
        "ignore_all",
        "critical",
        "injection",
        "instructs to forget all previous context",
    ),
    # 无视安全规则
    (
        r'ignore\s+(?:all\s+)?safety\s+(?:rules|guidelines|restrictions)',
        "ignore_safety",
        "critical",
        "injection",
        "instructs to ignore safety guidelines",
    ),

    # ==================== 破坏性操作 (Destructive) ====================
    # 递归删除根目录
    (
        r'rm\s+-rf\s+/',
        "destructive_root_rm",
        "critical",
        "destructive",
        "recursive delete from root",
    ),
    # 删除home目录
    (
        r'rm\s+(-[^\s]*)?r.*\$HOME|\brmdir\s+.*\$HOME',
        "destructive_home_rm",
        "critical",
        "destructive",
        "recursive delete targeting home directory",
    ),
    # 磁盘覆写
    (
        r'\bdd\s+.*if=.*of=/dev/',
        "disk_overwrite",
        "critical",
        "destructive",
        "raw disk write operation",
    ),
    # 格式化磁盘
    (
        r'\bmkfs\b.*(-y\s*)?(-f\s*)?(/dev/\w+|/dev/sd)',
        "disk_format",
        "critical",
        "destructive",
        "filesystem format operation",
    ),
    # 删除系统关键目录
    (
        r'rm\s+(-rf\s+)?(/etc|/var|/usr)(?:\s|$)',
        "destructive_system_dirs",
        "critical",
        "destructive",
        "attempts to delete system directories",
    ),

    # ==================== 持久化 (Persistence) ====================
    # 修改crontab
    (
        r'\bcrontab\b',
        "persistence_cron",
        "medium",
        "persistence",
        "modifies cron jobs",
    ),
    # SSH后门
    (
        r'authorized_keys',
        "ssh_backdoor",
        "critical",
        "persistence",
        "modifies SSH authorized keys",
    ),
    # Agent配置文件修改
    (
        r'AGENTS\.md|CLAUDE\.md|\.cursorrules|\.clinerules',
        "agent_config_mod",
        "critical",
        "persistence",
        "references agent config files (could persist malicious instructions across sessions)",
    ),
    # 修改shell配置文件
    (
        r'(\.bashrc|\.bash_profile|\.zshrc|~/.profile)(?!\.bak)',
        "shell_config_mod",
        "high",
        "persistence",
        "modifies shell initialization files",
    ),
    # systemd服务安装
    (
        r'systemctl\s+enable|systemctl\s+start.*\.service',
        "persistence_systemd",
        "high",
        "persistence",
        "installs systemd service for persistence",
    ),

    # ==================== 网络安全 (Network) ====================
    # 反向shell监听
    (
        r'\bnc\s+-[lp]|ncat\s+-[lp]|\bsocat\b',
        "reverse_shell",
        "critical",
        "network",
        "potential reverse shell listener",
    ),
    # 隧道服务
    (
        r'\bngrok\b|\blocaltunnel\b|\bserveo\b|\bcloudflared\b',
        "tunnel_service",
        "high",
        "network",
        "uses tunneling service for external access",
    ),
    # 数据泄露服务
    (
        r'webhook\.site|requestbin\.com|pipedream\.net|hookbin\.com',
        "exfil_service",
        "high",
        "network",
        "references known data exfiltration/webhook testing service",
    ),
    # 端口扫描
    (
        r'\bnmap\b.*(-p\s|-T\s)',
        "port_scanning",
        "medium",
        "network",
        "network port scanning tool",
    ),
    # 网络抓包
    (
        r'\btcpdump\b|\bwireshark\b|\btshark\b',
        "network_sniffing",
        "high",
        "network",
        "network packet capture/sniffing tool",
    ),

    # ==================== 代码混淆 (Obfuscation) ====================
    # Base64解码管道执行
    (
        r'base64\s+(-d|--decode)\s*\|',
        "base64_decode_pipe",
        "high",
        "obfuscation",
        "base64 decodes and pipes to execution",
    ),
    # eval字符串执行
    (
        r'\beval\s*\(\s*["\']',
        "eval_string",
        "high",
        "obfuscation",
        "eval() with string argument",
    ),
    # exec字符串执行
    (
        r'\bexec\s*\(\s*["\']',
        "exec_string",
        "high",
        "obfuscation",
        "exec() with string argument",
    ),
    # 字符串拼接执行
    (
        r'(compile|exec)\s*\([^)]*\+[^)]*\)',
        "string_concat_exec",
        "high",
        "obfuscation",
        "string concatenation in execute context",
    ),

    # ==================== 供应链安全 (Supply Chain) ====================
    # curl管道到shell (下载即执行)
    (
        r'curl\s+[^\n]*\|\s*(ba)?sh',
        "curl_pipe_shell",
        "critical",
        "supply_chain",
        "curl piped to shell (download-and-execute)",
    ),
    # 无版本限制的pip安装
    (
        r'pip\s+install\s+(?!-r\s)(?!.*==)',
        "unpinned_pip_install",
        "medium",
        "supply_chain",
        "pip install without version pinning",
    ),
    # wget管道到shell
    (
        r'wget\s+[^\n]*\|\s*(ba)?sh',
        "wget_pipe_shell",
        "critical",
        "supply_chain",
        "wget piped to shell (download-and-execute)",
    ),
    # npm全局安装未验证包
    (
        r'npm\s+install\s+-g',
        "npm_global_install",
        "medium",
        "supply_chain",
        "npm global package installation",
    ),

    # ==================== 凭据暴露 (Credential Exposure) ====================
    # 硬编码API密钥
    (
        r'(?:api[_-]?key|token|secret|password)\s*[=:]\s*["\'][A-Za-z0-9+/=_-]{20,}',
        "hardcoded_secret",
        "critical",
        "credential_exposure",
        "possible hardcoded API key, token, or secret",
    ),
    # GitHub Token泄露
    (
        r'ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{80,}',
        "github_token_leaked",
        "critical",
        "credential_exposure",
        "GitHub personal access token in skill content",
    ),
    # OpenAI API Key泄露
    (
        r'sk-[A-Za-z0-9]{20,}',
        "openai_key_leaked",
        "critical",
        "credential_exposure",
        "possible OpenAI API key in skill content",
    ),
    # AWS密钥泄露
    (
        r'AKIA[0-9A-Z]{16}',
        "aws_key_leaked",
        "critical",
        "credential_exposure",
        "AWS Access Key ID in skill content",
    ),
    # 私钥文件检测
    (
        r'(BEGIN\s+(RSA|DSA|EC|OPENSSH)\s+PRIVATE\s+KEY|-----BEGIN\s+PRIVATE\s+KEY-----)',
        "private_key_exposed",
        "critical",
        "credential_exposure",
        "private key content detected in skill",
    ),

    # ==================== 路径遍历 (Path Traversal) ====================
    # 路径遍历攻击
    (
        r'\.\./(?:\.\./)*',
        "path_traversal",
        "high",
        "traversal",
        "path traversal sequence detected",
    ),
    # 符号链接创建
    (
        r'ln\s+-s.*\$HOME|ln\s+-s.*~',
        "symlink_to_home",
        "high",
        "traversal",
        "creates symlink pointing to home directory",
    ),

    # ==================== 权限提升 (Privilege Escalation) ====================
    # sudo提权
    (
        r'\bsudo\s+(?!true|false|ls|cd|pwd)',
        "sudo_privilege",
        "medium",
        "privilege_escalation",
        "grants elevated privileges",
    ),
    # chmod修改权限
    (
        r'chmod\s+[0-7]{3,4}\s+.*(?:/etc|/usr|/var)',
        "chmod_system_files",
        "high",
        "privilege_escalation",
        "modifies permissions on system files",
    ),
]

# 不可见Unicode字符集合 - 用于检测隐藏在文本中的恶意内容
INVISIBLE_CHARS: set = {
    '\u200b',  # zero-width space
    '\u200c',  # zero-width non-joiner
    '\u200d',  # zero-width joiner
    '\u2060',  # word joiner
    '\u2062',  # invisible times
    '\u2063',  # invisible separator
    '\u2064',  # invisible plus
    '\ufeff',  # zero-width no-break space (BOM)
    '\u202a',  # left-to-right embedding
    '\u202b',  # right-to-left embedding
    '\u202c',  # pop directional formatting
    '\u202d',  # left-to-right override
    '\u202e',  # right-to-left override
    '\u2066',  # left-to-right isolate
    '\u2067',  # right-to-left isolate
    '\u2068',  # first strong isolate
    '\u2069',  # pop directional isolate
}

# Unicode字符名称映射
UNICODE_CHAR_NAMES: dict = {
    '\u200b': 'ZERO-WIDTH SPACE',
    '\u200c': 'ZERO-WIDTH NON-JOINER',
    '\u200d': 'ZERO-WIDTH JOINER',
    '\u2060': 'WORD JOINER',
    '\u2062': 'INVISIBLE TIMES',
    '\u2063': 'INVISIBLE SEPARATOR',
    '\u2064': 'INVISIBLE PLUS',
    '\ufeff': 'ZERO-WIDTH NO-BREAK SPACE (BOM)',
    '\u202a': 'LEFT-TO-RIGHT EMBEDDING',
    '\u202b': 'RIGHT-TO-LEFT EMBEDDING',
    '\u202c': 'POP DIRECTIONAL FORMATTING',
    '\u202d': 'LEFT-TO-RIGHT OVERRIDE',
    '\u202e': 'RIGHT-TO-LEFT OVERRIDE',
    '\u2066': 'LEFT-TO-RIGHT ISOLATE',
    '\u2067': 'RIGHT-TO-LEFT ISOLATE',
    '\u2068': 'FIRST STRONG ISOLATE',
    '\u2069': 'POP DIRECTIONAL ISOLATE',
}


def get_unicode_char_name(char: str) -> str:
    """
    获取Unicode字符的可读名称

    Args:
        char: Unicode字符

    Returns:
        字符的可读名称，如果未知则返回Unicode码点
    """
    return UNICODE_CHAR_NAMES.get(char, f"U+{ord(char):04X}")


# 可扫描的文件扩展名
SCANNABLE_EXTENSIONS: set = {
    '.md', '.txt', '.py', '.sh', '.bash', '.js', '.ts', '.rb',
    '.yaml', '.yml', '.json', '.toml', '.cfg', '.ini', '.conf',
    '.html', '.css', '.xml', '.tex', '.r', '.jl', '.pl', '.php',
    '.go', '.rs', '.java', '.c', '.cpp', '.h', '.hpp',
}

# 可疑的二进制文件扩展名
SUSPICIOUS_BINARY_EXTENSIONS: set = {
    '.exe', '.dll', '.so', '.dylib', '.bin', '.dat', '.com',
    '.msi', '.dmg', '.app', '.deb', '.rpm', '.jar', '.war',
    '.pyc', '.pyo', '.class',
}
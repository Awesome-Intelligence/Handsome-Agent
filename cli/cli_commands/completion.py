#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Completion - Shell completion utilities.

🚪 Access - 💬 CLI - Shell 补全

提供 bash/zsh/fish 的命令补全支持。
"""

import os
import sys
from pathlib import Path
from typing import List, Optional


def get_bash_completion_script() -> str:
    """Generate bash completion script.

    Returns:
        Bash completion script content
    """
    return '''#!/bin/bash
# Agent-Z Bash Completion

_agentz()
{
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    opts="chat setup status model skills config auth profile doctor help version"
    opts+=" --help --version --interactive --query --model --provider"

    case "${prev}" in
        chat)
            COMPREPLY=($(compgen -W "-q --model --provider" -- "${cur}"))
            ;;
        setup)
            COMPREPLY=($(compgen -W "--quick --full" -- "${cur}"))
            ;;
        model)
            COMPREPLY=($(compgen -W "list set" -- "${cur}"))
            ;;
        skills)
            COMPREPLY=($(compgen -W "list search install" -- "${cur}"))
            ;;
        config)
            COMPREPLY=($(compgen -W "show edit set get" -- "${cur}"))
            ;;
        profile)
            COMPREPLY=($(compgen -W "list create delete use" -- "${cur}"))
            ;;
        auth)
            COMPREPLY=($(compgen -W "list add remove reset" -- "${cur}"))
            ;;
        *)
            COMPREPLY=($(compgen -W "${opts}" -- "${cur}"))
            ;;
    esac

    return 0
}

complete -F _agentz agentz
'''


def get_zsh_completion_script() -> str:
    """Generate zsh completion script.

    Returns:
        Zsh completion script content
    """
    return '''#!/usr/bin/env zsh
# Agent-Z Zsh Completion

_agentz()
{
    local -a commands
    commands=(
        'chat:Start interactive chat'
        'setup:Run setup wizard'
        'status:Show system status'
        'model:Model management'
        'skills:Skills management'
        'config:Configuration management'
        'auth:Authentication management'
        'profile:Profile management'
        'doctor:Run diagnostics'
        'help:Show help'
        'version:Show version'
    )

    _describe 'command' commands
}

compdef _agentz agentz
'''


def install_bash_completion():
    """Install bash completion script."""
    completion_dir = Path.home() / ".bash_completion.d"
    completion_dir.mkdir(exist_ok=True)

    script_path = completion_dir / "agentz"
    script_path.write_text(get_bash_completion_script())

    print(f"Bash completion installed to: {script_path}")
    print("Add to ~/.bashrc: source ~/.bash_completion.d/agentz")


def install_zsh_completion():
    """Install zsh completion script."""
    completion_dir = Path.home() / ".zsh/completion"
    completion_dir.mkdir(parents=True, exist_ok=True)

    script_path = completion_dir / "_agentz"
    script_path.write_text(get_zsh_completion_script())

    print(f"Zsh completion installed to: {script_path}")
    print("Add to ~/.zshrc: fpath=(~/.zsh/completion $fpath)")


def print_completion_script(shell: str = "bash"):
    """Print completion script for a shell.

    Args:
        shell: Shell type ('bash' or 'zsh')
    """
    if shell == "bash":
        print(get_bash_completion_script())
    elif shell == "zsh":
        print(get_zsh_completion_script())
    else:
        print(f"Unknown shell: {shell}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "install":
            shell = sys.argv[2] if len(sys.argv) > 2 else "bash"
            if shell == "bash":
                install_bash_completion()
            elif shell == "zsh":
                install_zsh_completion()

        elif command == "print":
            shell = sys.argv[2] if len(sys.argv) > 2 else "bash"
            print_completion_script(shell)

    else:
        print("Usage:")
        print("  agentz completion install [bash|zsh]")
        print("  agentz completion print [bash|zsh]")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HermesCLI - Interactive Terminal UI

Inspired by Hermes Agent's cli.py
"""

import argparse
import asyncio
import logging
import sys
import os

from cli.main import main as cli_main


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog='awesome-agent',
        description='Handsome Agent - An AI-powered assistant inspired by Hermes Agent'
    )
    
    # Main commands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Interactive mode
    subparsers.add_parser('chat', help='Start interactive chat mode')
    
    # Setup command
    subparsers.add_parser('setup', help='Run setup wizard')
    
    # List sessions
    subparsers.add_parser('sessions', help='List all sessions')
    
    # Run batch
    batch_parser = subparsers.add_parser('batch', help='Run batch processing')
    batch_parser.add_argument('--input', '-i', help='Input file')
    batch_parser.add_argument('--output', '-o', help='Output file')
    
    # Version
    subparsers.add_parser('version', help='Show version')
    
    # Debug mode
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug logging')
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()
    
    # Set up logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Handle commands
    if args.command == 'setup':
        from cli.setup_wizard import run_setup_wizard
        run_setup_wizard()
    elif args.command == 'sessions':
        list_sessions()
    elif args.command == 'batch':
        run_batch(args)
    elif args.command == 'version':
        show_version()
    elif args.command == 'chat' or args.command is None:
        asyncio.run(cli_main())
    else:
        print(f"Unknown command: {args.command}")
        sys.exit(1)


def list_sessions():
    """List all sessions."""
    from hermes_state import HermesState
    
    state = HermesState()
    sessions = state.list_sessions()
    
    if not sessions:
        print("No sessions found.")
        return
    
    print("Available sessions:")
    for session_id in sessions:
        print(f"  - {session_id}")
    
    state.close()


def run_batch(args):
    """Run batch processing."""
    if not args.input:
        print("Error: --input is required for batch mode")
        sys.exit(1)
    
    print(f"Running batch processing with input: {args.input}")
    # Batch processing logic would go here
    # This is a placeholder
    if os.path.exists(args.input):
        print(f"Processing file: {args.input}")
        if args.output:
            print(f"Output will be saved to: {args.output}")
    else:
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1)


def show_version():
    """Show version information."""
    print("Handsome Agent v1.0.0")
    print("Inspired by Hermes Agent")


if __name__ == '__main__':
    main()

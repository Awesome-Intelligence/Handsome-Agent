#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch Runner Module - Inspired by Hermes Agent's batch_runner.py

Handles batch trajectory generation and processing.
"""

import asyncio
import json
import os
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging

from run_agent import AIAgent, AgentConfig
from hermes_state import HermesState


@dataclass
class BatchInput:
    """Input for batch processing."""
    tasks: List[Dict[str, Any]]
    config: Optional[Dict[str, Any]] = None


@dataclass
class BatchResult:
    """Result of batch processing."""
    task_id: str
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    timestamp: float = 0.0


@dataclass
class BatchReport:
    """Report of batch processing."""
    batch_id: str
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    total_execution_time: float
    results: List[BatchResult]
    start_time: float = 0.0
    end_time: float = 0.0


class BatchRunner:
    """
    Batch processing runner for agent tasks.
    
    Inspired by Hermes Agent's batch_runner.py
    """
    
    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.agent = None
    
    async def initialize_agent(self):
        """Initialize the agent."""
        self.agent = AIAgent(self.config)
        self.logger.info("Batch runner agent initialized")
    
    async def run_task(self, task: Dict[str, Any]) -> BatchResult:
        """
        Run a single task.
        
        Args:
            task: Task dictionary with 'id' and 'input' keys
        
        Returns:
            BatchResult containing task execution result
        """
        task_id = task.get("id", f"task_{datetime.now().timestamp()}")
        user_input = task.get("input", "")
        
        start_time = datetime.now().timestamp()
        
        try:
            if not self.agent:
                await self.initialize_agent()
            
            # Execute task
            response = await self.agent.respond(user_input)
            
            end_time = datetime.now().timestamp()
            
            return BatchResult(
                task_id=task_id,
                success=True,
                output=response.content,
                execution_time=end_time - start_time,
                timestamp=end_time
            )
        
        except Exception as e:
            end_time = datetime.now().timestamp()
            self.logger.error(f"Task {task_id} failed: {e}")
            
            return BatchResult(
                task_id=task_id,
                success=False,
                error=str(e),
                execution_time=end_time - start_time,
                timestamp=end_time
            )
    
    async def run_batch(self, input_data: BatchInput) -> BatchReport:
        """
        Run a batch of tasks.
        
        Args:
            input_data: BatchInput containing tasks and config
        
        Returns:
            BatchReport with processing results
        """
        batch_id = f"batch_{datetime.now().timestamp()}"
        start_time = datetime.now().timestamp()
        
        self.logger.info(f"Starting batch processing: {batch_id}")
        self.logger.info(f"Processing {len(input_data.tasks)} tasks")
        
        results = []
        successful = 0
        failed = 0
        
        # Process tasks sequentially
        for task in input_data.tasks:
            result = await self.run_task(task)
            results.append(result)
            
            if result.success:
                successful += 1
            else:
                failed += 1
            
            self.logger.debug(f"Task {result.task_id}: {'SUCCESS' if result.success else 'FAILED'}")
        
        end_time = datetime.now().timestamp()
        total_time = end_time - start_time
        
        report = BatchReport(
            batch_id=batch_id,
            total_tasks=len(input_data.tasks),
            successful_tasks=successful,
            failed_tasks=failed,
            total_execution_time=total_time,
            results=results,
            start_time=start_time,
            end_time=end_time
        )
        
        self.logger.info(f"Batch {batch_id} completed: {successful}/{len(input_data.tasks)} successful")
        self.logger.info(f"Total execution time: {total_time:.2f} seconds")
        
        return report
    
    async def run_from_file(self, input_file: str, output_file: Optional[str] = None) -> BatchReport:
        """
        Run batch processing from an input file.
        
        Args:
            input_file: Path to input JSON file
            output_file: Optional output file path
        
        Returns:
            BatchReport with processing results
        """
        # Load input
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        batch_input = BatchInput(
            tasks=data.get("tasks", []),
            config=data.get("config", {})
        )
        
        # Run batch
        report = await self.run_batch(batch_input)
        
        # Save output if specified
        if output_file:
            self.save_report(report, output_file)
        
        return report
    
    def save_report(self, report: BatchReport, output_file: str):
        """
        Save batch report to file.
        
        Args:
            report: BatchReport to save
            output_file: Output file path
        """
        report_dict = {
            "batch_id": report.batch_id,
            "total_tasks": report.total_tasks,
            "successful_tasks": report.successful_tasks,
            "failed_tasks": report.failed_tasks,
            "total_execution_time": report.total_execution_time,
            "start_time": report.start_time,
            "end_time": report.end_time,
            "results": [
                {
                    "task_id": r.task_id,
                    "success": r.success,
                    "output": r.output,
                    "error": r.error,
                    "execution_time": r.execution_time,
                    "timestamp": r.timestamp
                }
                for r in report.results
            ]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"Batch report saved to: {output_file}")


async def main():
    """Main entry point for batch runner."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch Runner")
    parser.add_argument("--input", "-i", required=True, help="Input JSON file")
    parser.add_argument("--output", "-o", help="Output JSON file")
    
    args = parser.parse_args()
    
    runner = BatchRunner()
    await runner.run_from_file(args.input, args.output)


if __name__ == "__main__":
    asyncio.run(main())

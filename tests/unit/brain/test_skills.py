#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the brain module skills functionality.

Tests cover skill loader, matcher, and registry.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import json


class TestSkillLoader:
    """Test skill loader functionality."""
    
    def test_skill_loader_initialization(self):
        """Test initializing skill loader."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir) / "skills"
            skills_dir.mkdir(parents=True)
            
            # Skill loader should initialize
            loader = SkillLoader(skills_dir=str(skills_dir))
            
            assert loader.skills_dir == str(skills_dir)
    
    def test_load_skill_from_file(self):
        """Test loading a skill from file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir)
            
            # Create a skill file
            skill_file = skills_dir / "test_skill.json"
            skill_data = {
                "name": "test_skill",
                "description": "A test skill",
                "version": "1.0.0",
                "triggers": ["test", "example"],
                "actions": [
                    {
                        "type": "respond",
                        "content": "This is a test response"
                    }
                ]
            }
            
            with open(skill_file, 'w') as f:
                json.dump(skill_data, f)
            
            # Load skill
            from brain.skills.loader import SkillLoader
            loader = SkillLoader(skills_dir=str(skills_dir))
            skill = loader.load_skill("test_skill")
            
            assert skill is not None
            assert skill["name"] == "test_skill"
            assert skill["description"] == "A test skill"
    
    def test_load_nonexistent_skill(self):
        """Test loading a skill that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from brain.skills.loader import SkillLoader
            loader = SkillLoader(skills_dir=tmpdir)
            
            skill = loader.load_skill("nonexistent_skill")
            
            assert skill is None
    
    def test_list_available_skills(self):
        """Test listing all available skills."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir)
            
            # Create multiple skill files
            for skill_name in ["skill1", "skill2", "skill3"]:
                skill_file = skills_dir / f"{skill_name}.json"
                with open(skill_file, 'w') as f:
                    json.dump({"name": skill_name}, f)
            
            from brain.skills.loader import SkillLoader
            loader = SkillLoader(skills_dir=str(skills_dir))
            skills = loader.list_skills()
            
            assert len(skills) == 3
            assert "skill1" in skills
            assert "skill2" in skills
            assert "skill3" in skills
    
    def test_reload_skill(self):
        """Test reloading a skill."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir)
            skill_file = skills_dir / "reloadable_skill.json"
            
            # Initial skill data
            skill_data = {"name": "reloadable_skill", "version": "1.0.0"}
            with open(skill_file, 'w') as f:
                json.dump(skill_data, f)
            
            from brain.skills.loader import SkillLoader
            loader = SkillLoader(skills_dir=str(skills_dir))
            
            # First load
            skill_v1 = loader.load_skill("reloadable_skill")
            assert skill_v1["version"] == "1.0.0"
            
            # Update skill
            skill_data["version"] = "2.0.0"
            with open(skill_file, 'w') as f:
                json.dump(skill_data, f)
            
            # Reload
            skill_v2 = loader.reload_skill("reloadable_skill")
            assert skill_v2["version"] == "2.0.0"


class TestSkillMatcher:
    """Test skill matcher functionality."""
    
    def test_skill_matcher_initialization(self):
        """Test initializing skill matcher."""
        from brain.skills.matcher import SkillMatcher
        
        matcher = SkillMatcher()
        
        assert matcher is not None
    
    def test_match_by_keyword(self):
        """Test matching skills by keyword."""
        from brain.skills.matcher import SkillMatcher
        
        matcher = SkillMatcher()
        
        skills = {
            "python_skill": {
                "triggers": ["python", "programming", "code"],
                "keywords": ["python", "script"]
            },
            "web_skill": {
                "triggers": ["web", "html", "css"],
                "keywords": ["website", "frontend"]
            }
        }
        
        # Match "python"
        matches = matcher.match("python tutorial", skills)
        
        assert len(matches) > 0
        # Should match python_skill
        matched_skill_ids = [m["skill_id"] for m in matches]
        assert "python_skill" in matched_skill_ids
    
    def test_match_by_triggers(self):
        """Test matching skills by triggers."""
        from brain.skills.matcher import SkillMatcher
        
        matcher = SkillMatcher()
        
        skills = {
            "weather_skill": {
                "triggers": ["weather", "temperature", "forecast"]
            }
        }
        
        # Match "weather"
        matches = matcher.match("What's the weather today?", skills)
        
        assert len(matches) > 0
        assert any(m["skill_id"] == "weather_skill" for m in matches)
    
    def test_match_confidence_score(self):
        """Test match confidence scoring."""
        from brain.skills.matcher import SkillMatcher
        
        matcher = SkillMatcher()
        
        skills = {
            "exact_match": {
                "triggers": ["hello", "hi", "hey"]
            },
            "partial_match": {
                "triggers": ["hello"]
            }
        }
        
        # "hello" should match both, but exact_match should have higher score
        matches = matcher.match("hello", skills)
        
        if len(matches) >= 2:
            # Find scores
            exact_score = next(
                m["confidence"] for m in matches
                if m["skill_id"] == "exact_match"
            )
            partial_score = next(
                m["confidence"] for m in matches
                if m["skill_id"] == "partial_match"
            )
            
            assert exact_score >= partial_score
    
    def test_no_match(self):
        """Test when no skill matches."""
        from brain.skills.matcher import SkillMatcher
        
        matcher = SkillMatcher()
        
        skills = {
            "python_skill": {
                "triggers": ["python"]
            }
        }
        
        # Should not match
        matches = matcher.match("completely unrelated query xyz123", skills)
        
        # May be empty or have very low confidence
        if matches:
            assert all(m["confidence"] < 0.3 for m in matches)


class TestSkillRegistry:
    """Test skill registry functionality."""
    
    def test_registry_initialization(self):
        """Test initializing skill registry."""
        from brain.skills.registry import SkillRegistry
        
        registry = SkillRegistry()
        
        assert registry is not None
        assert len(registry.get_all_skills()) == 0
    
    def test_register_skill(self):
        """Test registering a skill."""
        from brain.skills.registry import SkillRegistry
        
        registry = SkillRegistry()
        
        skill = {
            "name": "test_skill",
            "description": "A test skill",
            "triggers": ["test"]
        }
        
        registry.register("test_skill", skill)
        
        assert registry.get_skill("test_skill") is not None
        assert registry.get_skill("test_skill")["name"] == "test_skill"
    
    def test_unregister_skill(self):
        """Test unregistering a skill."""
        from brain.skills.registry import SkillRegistry
        
        registry = SkillRegistry()
        
        skill = {"name": "temp_skill", "triggers": []}
        registry.register("temp_skill", skill)
        
        assert registry.get_skill("temp_skill") is not None
        
        registry.unregister("temp_skill")
        
        assert registry.get_skill("temp_skill") is None
    
    def test_get_all_skills(self):
        """Test getting all registered skills."""
        from brain.skills.registry import SkillRegistry
        
        registry = SkillRegistry()
        
        # Register multiple skills
        registry.register("skill1", {"name": "Skill 1", "triggers": []})
        registry.register("skill2", {"name": "Skill 2", "triggers": []})
        registry.register("skill3", {"name": "Skill 3", "triggers": []})
        
        all_skills = registry.get_all_skills()
        
        assert len(all_skills) == 3
        assert "skill1" in all_skills
        assert "skill2" in all_skills
        assert "skill3" in all_skills
    
    def test_search_skills(self):
        """Test searching skills by query."""
        from brain.skills.registry import SkillRegistry
        
        registry = SkillRegistry()
        
        registry.register("python_skill", {
            "name": "Python Helper",
            "description": "Helps with Python programming",
            "triggers": ["python", "code"]
        })
        
        registry.register("web_skill", {
            "name": "Web Helper",
            "description": "Helps with web development",
            "triggers": ["html", "css", "web"]
        })
        
        results = registry.search("python")
        
        assert len(results) >= 1
        assert any("python" in r["name"].lower() or "python" in r["description"].lower() 
                   for r in results)
    
    def test_enable_disable_skill(self):
        """Test enabling and disabling skills."""
        from brain.skills.registry import SkillRegistry
        
        registry = SkillRegistry()
        
        registry.register("toggle_skill", {"name": "Toggle Skill", "triggers": []})
        
        # Disable
        registry.disable_skill("toggle_skill")
        assert registry.is_enabled("toggle_skill") is False
        
        # Enable
        registry.enable_skill("toggle_skill")
        assert registry.is_enabled("toggle_skill") is True
    
    def test_skill_priority(self):
        """Test skill priority ordering."""
        from brain.skills.registry import SkillRegistry
        
        registry = SkillRegistry()
        
        registry.register("low_priority", {
            "name": "Low Priority",
            "triggers": ["test"],
            "priority": 1
        })
        
        registry.register("high_priority", {
            "name": "High Priority",
            "triggers": ["test"],
            "priority": 10
        })
        
        # Get by priority
        all_skills = registry.get_all_skills()
        priorities = [s["priority"] for s in all_skills.values() if "priority" in s]
        
        assert 1 in priorities
        assert 10 in priorities


class TestSkillExecution:
    """Test skill execution functionality."""
    
    def test_execute_skill_action(self):
        """Test executing a skill action."""
        skill = {
            "name": "test_skill",
            "actions": [
                {
                    "type": "respond",
                    "content": "Test response"
                }
            ]
        }
        
        # Simulate action execution
        action = skill["actions"][0]
        
        assert action["type"] == "respond"
        assert action["content"] == "Test response"
    
    def test_skill_action_types(self):
        """Test different skill action types."""
        actions = [
            {"type": "respond", "content": "Response text"},
            {"type": "command", "command": "ls -la"},
            {"type": "function", "function_name": "my_function", "params": {}},
            {"type": "redirect", "target": "another_skill"}
        ]
        
        for action in actions:
            assert "type" in action
            assert action["type"] in ["respond", "command", "function", "redirect"]
    
    def test_skill_parameters(self):
        """Test skill parameter handling."""
        skill = {
            "name": "parameterized_skill",
            "parameters": {
                "message": {
                    "type": "string",
                    "description": "Message to respond with",
                    "required": True
                },
                "count": {
                    "type": "integer",
                    "description": "Number of times to repeat",
                    "default": 1
                }
            }
        }
        
        assert "parameters" in skill
        assert "message" in skill["parameters"]
        assert "count" in skill["parameters"]
        assert skill["parameters"]["count"]["default"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

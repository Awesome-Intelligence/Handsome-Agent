#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for agent/skill_recommender.py
"""

import pytest
from agent.skill_recommender import (
    SkillRecommender,
    SkillInfo,
    RecommenderConfig,
    RecommendationScore,
    create_recommender_from_skills,
)


class TestSkillRecommender:
    """Test SkillRecommender functionality"""

    def test_add_skill(self):
        """Test adding skills"""
        recommender = SkillRecommender()
        skill = SkillInfo(
            skill_id="code-review",
            name="Code Review",
            description="Review code for bugs",
            usage_count=10,
        )
        recommender.add_skill(skill)

        assert len(recommender._skills) == 1
        assert recommender._skills["code-review"].skill_id == "code-review"

    def test_recommend_by_description(self):
        """Test recommendation by description"""
        recommender = SkillRecommender()

        # Add skills
        recommender.add_skill(SkillInfo(
            skill_id="code-review",
            name="Code Review",
            description="Review code for bugs and issues",
            usage_count=10,
        ))
        recommender.add_skill(SkillInfo(
            skill_id="code-generator",
            name="Code Generator",
            description="Generate code from templates",
            usage_count=5,
        ))

        results = recommender.recommend_by_description(
            "I need to review code for bugs",
            top_n=2
        )

        assert len(results) > 0
        assert results[0].skill.skill_id == "code-review"
        assert len(results[0].matched_keywords) > 0

    def test_recommend_by_description_no_match(self):
        """Test recommendation with no match"""
        recommender = SkillRecommender()

        recommender.add_skill(SkillInfo(
            skill_id="code-review",
            name="Code Review",
            description="Review code",
        ))

        results = recommender.recommend_by_description(
            "cook dinner recipe",
            top_n=5
        )

        # No match should return empty
        assert len(results) == 0

    def test_recommend_by_history(self):
        """Test recommendation by history"""
        recommender = SkillRecommender()

        # Add skills
        recommender.add_skill(SkillInfo(
            skill_id="code-review",
            name="Code Review",
            description="Review code",
            usage_count=10,
        ))
        recommender.add_skill(SkillInfo(
            skill_id="testing",
            name="Testing",
            description="Write tests",
            usage_count=5,
        ))

        # Recommend based on history
        results = recommender.recommend_by_history(
            ["code-review", "other-skill"],
            top_n=2
        )

        assert len(results) > 0
        # code-review should score high due to direct match
        assert any(r.skill.skill_id == "code-review" for r in results)

    def test_recommend_top_frequent(self):
        """Test top frequent recommendations"""
        recommender = SkillRecommender()

        recommender.add_skill(SkillInfo(
            skill_id="skill-a",
            name="Skill A",
            description="A skill",
            usage_count=100,
        ))
        recommender.add_skill(SkillInfo(
            skill_id="skill-b",
            name="Skill B",
            description="B skill",
            usage_count=50,
        ))
        recommender.add_skill(SkillInfo(
            skill_id="skill-c",
            name="Skill C",
            description="C skill",
            usage_count=10,
        ))

        results = recommender.recommend_top_frequent(top_n=3)

        assert len(results) == 3
        assert results[0].skill.skill_id == "skill-a"
        assert results[1].skill.skill_id == "skill-b"
        assert results[2].skill.skill_id == "skill-c"

    def test_recommend_combined(self):
        """Test combined recommendation"""
        recommender = SkillRecommender()

        recommender.add_skill(SkillInfo(
            skill_id="code-review",
            name="Code Review",
            description="Review code for bugs",
            usage_count=100,
        ))
        recommender.add_skill(SkillInfo(
            skill_id="testing",
            name="Testing",
            description="Write and run tests",
            usage_count=50,
        ))

        results = recommender.recommend(
            description="code testing",
            history_skill_ids=["code-review"],
            top_n=5
        )

        assert len(results) > 0

    def test_skip_inactive_skills(self):
        """Test that inactive skills are skipped"""
        recommender = SkillRecommender()

        recommender.add_skill(SkillInfo(
            skill_id="active-skill",
            name="Active Skill",
            description="An active skill",
            state="active",
            usage_count=100,
        ))
        recommender.add_skill(SkillInfo(
            skill_id="archived-skill",
            name="Archived Skill",
            description="An archived skill",
            state="archived",
            usage_count=200,
        ))

        results = recommender.recommend_top_frequent(top_n=5)

        skill_ids = [r.skill.skill_id for r in results]
        assert "active-skill" in skill_ids
        assert "archived-skill" not in skill_ids

    def test_get_skill_by_id(self):
        """Test getting skill by ID"""
        recommender = SkillRecommender()

        recommender.add_skill(SkillInfo(
            skill_id="test-skill",
            name="Test Skill",
            description="A test",
        ))

        skill = recommender.get_skill_by_id("test-skill")
        assert skill is not None
        assert skill.skill_id == "test-skill"

        missing = recommender.get_skill_by_id("nonexistent")
        assert missing is None

    def test_get_all_skills(self):
        """Test getting all skills"""
        recommender = SkillRecommender()

        recommender.add_skill(SkillInfo(
            skill_id="skill-1",
            name="Skill 1",
            description="First skill",
        ))
        recommender.add_skill(SkillInfo(
            skill_id="skill-2",
            name="Skill 2",
            description="Second skill",
        ))

        all_skills = recommender.get_all_skills()
        assert len(all_skills) == 2

    def test_clear_skills(self):
        """Test clearing skills"""
        recommender = SkillRecommender()

        recommender.add_skill(SkillInfo(
            skill_id="test",
            name="Test",
            description="Test",
        ))

        assert len(recommender._skills) == 1
        recommender.clear_skills()
        assert len(recommender._skills) == 0

    def test_recommend_by_description_with_tags(self):
        """Test recommendation with tags"""
        recommender = SkillRecommender()

        recommender.add_skill(SkillInfo(
            skill_id="code-review",
            name="Code Review",
            description="Review code for bugs",
            tags=["coding", "review"],
        ))
        recommender.add_skill(SkillInfo(
            skill_id="testing",
            name="Testing",
            description="Write tests",
            tags=["testing", "qa"],
        ))

        # Query should match tags
        results = recommender.recommend_by_description("coding testing", top_n=1)

        assert len(results) > 0


class TestCreateRecommenderFromSkills:
    """Test create_recommender_from_skills"""

    def test_create_from_dict(self):
        """Test creating recommender from dict list"""
        skills_data = [
            {
                "skill_id": "skill-1",
                "name": "Skill 1",
                "description": "First skill",
                "tags": ["tag1"],
                "usage_count": 10,
                "state": "active",
            },
            {
                "skill_id": "skill-2",
                "name": "Skill 2",
                "description": "Second skill",
                "tags": ["tag2"],
                "usage_count": 5,
                "state": "active",
            },
        ]

        recommender = create_recommender_from_skills(skills_data)

        assert len(recommender._skills) == 2
        assert recommender.get_skill_by_id("skill-1") is not None
        assert recommender.get_skill_by_id("skill-2") is not None


class TestRecommenderConfig:
    """Test RecommenderConfig"""

    def test_default_config(self):
        """Test default configuration"""
        config = RecommenderConfig()

        assert config.max_results == 5
        assert config.frequency_weight == 0.3
        assert config.similarity_weight == 0.5
        assert config.history_weight == 0.2

    def test_custom_config(self):
        """Test custom configuration"""
        config = RecommenderConfig(
            max_results=10,
            frequency_weight=0.5,
            similarity_weight=0.3,
            history_weight=0.2,
        )

        assert config.max_results == 10
        assert config.frequency_weight == 0.5


class TestSkillInfo:
    """Test SkillInfo dataclass"""

    def test_create_skill_info(self):
        """Test creating SkillInfo"""
        skill = SkillInfo(
            skill_id="test",
            name="Test Skill",
            description="A test skill",
            tags=["testing", "test"],
            category="development",
            usage_count=10,
            state="active",
        )

        assert skill.skill_id == "test"
        assert skill.name == "Test Skill"
        assert skill.tags == ["testing", "test"]
        assert skill.usage_count == 10
        assert skill.state == "active"


class TestRecommendationScore:
    """Test RecommendationScore dataclass"""

    def test_create_recommendation_score(self):
        """Test creating RecommendationScore"""
        skill = SkillInfo(
            skill_id="test",
            name="Test",
            description="Test skill",
        )
        score = RecommendationScore(
            skill=skill,
            total_score=0.8,
            matched_keywords=["test", "code"],
        )

        assert score.skill.skill_id == "test"
        assert score.total_score == 0.8
        assert score.matched_keywords == ["test", "code"]

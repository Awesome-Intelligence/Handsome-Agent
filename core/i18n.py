#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Internationalization (i18n) Module for Handsome Agent
Provides multilingual support for logging and system messages.
Supports: Chinese (zh), English (en), Korean (ko), Japanese (ja)
"""

from typing import Dict, Optional


LAYER_EMOJI = {
    "user": "👤",
    "control": "🎛️",
    "reasoning": "🧠",
    "llm": "🤖",
    "tools": "🔧",
    "storage": "💾",
}


class I18n:
    """Internationalization handler for agent messages."""
    
    TRANSLATIONS: Dict[str, Dict[str, str]] = {
        "zh": {
            "flow_start": "👤 [用户层] 开始处理用户输入",
            "validation_pass": "🎛️ [控制层] 输入格式验证通过",
            "session_add": "💾 [存储层] 添加用户消息到会话",
            "cache_hit": "🎛️ [控制层] 缓存命中，跳过处理",
            "cache_miss": "🎛️ [控制层] 缓存未命中，执行正常流程",
            "processing_start": "🎛️ [控制层] 开始处理请求",
            "routing_enabled": "🎛️ [控制层] 启用路由功能，开始意图分类",
            "routing_match": "🎛️ [控制层] 找到匹配的路由",
            "routing_no_match": "🎛️ [控制层] 未找到匹配的路由，尝试技能执行",
            "skill_enabled": "🎛️ [控制层] 启用技能执行，开始意图分类",
            "skill_discovery": "🎛️ [控制层] 发现相关技能",
            "skill_execute": "🔧 [工具层] 执行技能",
            "skill_success": "🎛️ [控制层] 技能执行成功",
            "skill_fail": "🎛️ [控制层] 技能执行失败",
            "explanation_module": "🧠 [推理层] 使用解释模块生成响应",
            "response_complete": "🧠 [推理层] 响应生成完成",
            "session_add_assistant": "💾 [存储层] 添加助手响应到会话",
            "cache_store": "🎛️ [控制层] 存储响应到缓存",
            "complete": "🧠 [完成] 响应生成完成",
            "intent_classifying": "🎛️ [控制层] 正在对输入进行意图分类",
            "intent_result": "🎛️ [控制层] 分类结果",
            "intent_final": "🎛️ [控制层] 最终意图",
            "intent_default": "🎛️ [控制层] 未匹配到关键词，默认使用",
            "router_checking": "🎛️ [控制层] 检查注册的路由",
            "router_found": "🎛️ [控制层] 找到匹配路由",
            "skill_discovery_start": "🎛️ [控制层] 开始技能发现",
            "skill_manager_execute": "🔧 [工具层] 尝试执行技能",
            "skill_not_found": "🎛️ [控制层] 技能未找到",
            "skill_detail": "🔧 [工具层] 技能详情",
            "skill_validate_fail": "🎛️ [控制层] 参数验证失败",
            "skill_execute_start": "🔧 [工具层] 参数验证通过，开始执行",
            "skill_execute_success": "🎛️ [控制层] 技能执行成功",
            "skill_execute_error": "🎛️ [控制层] 技能执行异常",
            "session_add_msg": "💾 [存储层] 添加消息",
            "session_trim": "💾 [存储层] 历史记录已修剪",
            "flow_header": "=" * 70,
            
            "step_input": "👤 [用户层] 接收用户输入",
            "step_validation": "🎛️ [控制层] 输入格式验证通过",
            "step_session": "💾 [存储层] 消息已添加到会话",
            "step_cache_hit": "🎛️ [控制层] 缓存命中，跳过处理",
            "step_cache_miss": "🎛️ [控制层] 缓存未命中，执行正常流程",
            "step_processing": "🎛️ [控制层] 开始处理请求",
            "step_routing": "🎛️ [控制层] 进入任务路由模块",
            "step_skill": "🔧 [工具层] 进入技能管理器",
            "step_explanation": "🧠 [推理层] 调用解释模块处理请求",
            "step_complete": "🧠 [完成] 总耗时",
            
            "layer_user": "[用户层]",
            "layer_control": "[控制层]",
            "layer_reasoning": "[推理层]",
            "layer_llm": "[LLM层]",
            "layer_tools": "[工具层]",
            "layer_storage": "[存储层]",
        },
        "en": {
            "flow_start": "👤 [User Layer] Starting to process user input",
            "validation_pass": "🎛️ [Core Layer] Input validation passed",
            "session_add": "💾 [Storage Layer] Adding user message to session",
            "cache_hit": "🎛️ [Core Layer] Cache hit, skipping processing",
            "cache_miss": "🎛️ [Core Layer] Cache miss, continuing normal flow",
            "processing_start": "🎛️ [Core Layer] Starting request processing",
            "routing_enabled": "🎛️ [Core Layer] Routing enabled, starting intent classification",
            "routing_match": "🎛️ [Core Layer] Found matching route",
            "routing_no_match": "🎛️ [Core Layer] No matching route found, trying skills",
            "skill_enabled": "🎛️ [Core Layer] Skills enabled, starting intent classification",
            "skill_discovery": "🎛️ [Core Layer] Found relevant skills",
            "skill_execute": "🔧 [Tools Layer] Executing skill",
            "skill_success": "🎛️ [Core Layer] Skill executed successfully",
            "skill_fail": "🎛️ [Core Layer] Skill execution failed",
            "explanation_module": "🧠 [Reasoning Layer] Using explanation module to generate response",
            "response_complete": "🧠 [Reasoning Layer] Response generation complete",
            "session_add_assistant": "💾 [Storage Layer] Adding assistant response to session",
            "cache_store": "🎛️ [Core Layer] Storing response to cache",
            "complete": "🧠 [Complete] Response generation complete",
            "intent_classifying": "🎛️ [Core Layer] Classifying intent for input",
            "intent_result": "🎛️ [Core Layer] Classification result",
            "intent_final": "🎛️ [Core Layer] Final intent",
            "intent_default": "🎛️ [Core Layer] No keywords matched, using default",
            "router_checking": "🎛️ [Core Layer] Checking registered routes",
            "router_found": "🎛️ [Core Layer] Found matching routes",
            "skill_discovery_start": "🎛️ [Core Layer] Starting skill discovery",
            "skill_manager_execute": "🔧 [Tools Layer] Attempting to execute skill",
            "skill_not_found": "🎛️ [Core Layer] Skill not found",
            "skill_detail": "🔧 [Tools Layer] Skill details",
            "skill_validate_fail": "🎛️ [Core Layer] Parameter validation failed",
            "skill_execute_start": "🔧 [Tools Layer] Parameter validation passed, executing",
            "skill_execute_success": "🎛️ [Core Layer] Skill executed successfully",
            "skill_execute_error": "🎛️ [Core Layer] Skill execution error",
            "session_add_msg": "💾 [Storage Layer] Adding message",
            "session_trim": "💾 [Storage Layer] History trimmed",
            "flow_header": "=" * 70,
            
            "step_input": "👤 [User Layer] Received user input",
            "step_validation": "🎛️ [Core Layer] Input validation passed",
            "step_session": "💾 [Storage Layer] Message added to session",
            "step_cache_hit": "🎛️ [Core Layer] Cache hit, skipping",
            "step_cache_miss": "🎛️ [Core Layer] Cache miss, continuing",
            "step_processing": "🎛️ [Core Layer] Starting processing",
            "step_routing": "🎛️ [Core Layer] Entering task router",
            "step_skill": "🔧 [Tools Layer] Entering skill manager",
            "step_explanation": "🧠 [Reasoning Layer] Calling explanation module",
            "step_complete": "🧠 [Complete] Total time",
            
            "layer_user": "[User Layer]",
            "layer_control": "[Core Layer]",
            "layer_reasoning": "[Reasoning Layer]",
            "layer_llm": "[LLM Layer]",
            "layer_tools": "[Tools Layer]",
            "layer_storage": "[Storage Layer]",
        },
        "ko": {
            "flow_start": "👤 [사용자 계층] 사용자 입력 처리 시작",
            "validation_pass": "🎛️ [제어 계층] 입력 유효성 검사 통과",
            "session_add": "💾 [저장 계층] 세션에 사용자 메시지 추가",
            "cache_hit": "🎛️ [제어 계층] 캐시 히트, 처리 건너뛰기",
            "cache_miss": "🎛️ [제어 계층] 캐시 미스, 정상 처리 계속",
            "processing_start": "🎛️ [제어 계층] 요청 처리 시작",
            "routing_enabled": "🎛️ [제어 계층] 라우팅 활성화, 의도 분류 시작",
            "routing_match": "🎛️ [제어 계층] 매칭 라우트 발견",
            "routing_no_match": "🎛️ [제어 계층] 매칭 라우트 없음, 스킬 시도",
            "skill_enabled": "🎛️ [제어 계층] 스킬 활성화, 의도 분류 시작",
            "skill_discovery": "🎛️ [제어 계층] 관련 스킬 발견",
            "skill_execute": "🔧 [도구 계층] 스킬 실행",
            "skill_success": "🎛️ [제어 계층] 스킬 실행 성공",
            "skill_fail": "🎛️ [제어 계층] 스킬 실행 실패",
            "explanation_module": "🧠 [추론 계층] 설명 모듈로 응답 생성",
            "response_complete": "🧠 [추론 계층] 응답 생성 완료",
            "session_add_assistant": "💾 [저장 계층] 세션에 어시스턴트 응답 추가",
            "cache_store": "🎛️ [제어 계층] 응답을 캐시에 저장",
            "complete": "🧠 [완료] 응답 생성 완료",
            "intent_classifying": "🎛️ [제어 계층] 입력 의도 분류 중",
            "intent_result": "🎛️ [제어 계층] 분류 결과",
            "intent_final": "🎛️ [제어 계층] 최종 의도",
            "intent_default": "🎛️ [제어 계층] 키워드 미매칭, 기본값 사용",
            "router_checking": "🎛️ [제어 계층] 등록된 라우트 확인",
            "router_found": "🎛️ [제어 계층] 매칭 라우트 발견",
            "skill_discovery_start": "🎛️ [제어 계층] 스킬 발견 시작",
            "skill_manager_execute": "🔧 [도구 계층] 스킬 실행 시도",
            "skill_not_found": "🎛️ [제어 계층] 스킬을 찾을 수 없음",
            "skill_detail": "🔧 [도구 계층] 스킬 상세정보",
            "skill_validate_fail": "🎛️ [제어 계층] 매개변수 유효성 검사 실패",
            "skill_execute_start": "🔧 [도구 계층] 매개변수 유효성 검사 통과, 실행 시작",
            "skill_execute_success": "🎛️ [제어 계층] 스킬 실행 성공",
            "skill_execute_error": "🎛️ [제어 계층] 스킬 실행 오류",
            "session_add_msg": "💾 [저장 계층] 메시지 추가",
            "session_trim": "💾 [저장 계층] 히스토리 정리됨",
            "flow_header": "=" * 70,
            
            "step_input": "👤 [사용자 계층] 사용자 입력 수신",
            "step_validation": "🎛️ [제어 계층] 입력 유효성 검사 통과",
            "step_session": "💾 [저장 계층] 메시지가 세션에 추가됨",
            "step_cache_hit": "🎛️ [제어 계층] 캐시 히트, 건너뛰기",
            "step_cache_miss": "🎛️ [제어 계층] 캐시 미스, 계속",
            "step_processing": "🎛️ [제어 계층] 처리 시작",
            "step_routing": "🎛️ [제어 계층] 태스크 라우터 진입",
            "step_skill": "🔧 [도구 계층] 스킬 매니저 진입",
            "step_explanation": "🧠 [추론 계층] 설명 모듈 호출",
            "step_complete": "🧠 [완료] 총 소요 시간",
            
            "layer_user": "[사용자 계층]",
            "layer_control": "[제어 계층]",
            "layer_reasoning": "[추론 계층]",
            "layer_llm": "[LLM 계층]",
            "layer_tools": "[도구 계층]",
            "layer_storage": "[저장 계층]",
        },
        "ja": {
            "flow_start": "👤 [ユーザー層] ユーザー入力の処理を開始",
            "validation_pass": "🎛️ [コア層] 入力バリデーション合格",
            "session_add": "💾 [保存層] セッションにユーザーメッセージを追加",
            "cache_hit": "🎛️ [コア層] キャッシュヒット、処理をスキップ",
            "cache_miss": "🎛️ [コア層] キャッシュミス、通常処理を続行",
            "processing_start": "🎛️ [コア層] リクエスト処理を開始",
            "routing_enabled": "🎛️ [コア層] ルーティング有効化、意図分類を開始",
            "routing_match": "🎛️ [コア層] 一致するルートを発見",
            "routing_no_match": "🎛️ [コア層] 一致するルートなし、技能を試す",
            "skill_enabled": "🎛️ [コア層] スキル有効化、意図分類を開始",
            "skill_discovery": "🎛️ [コア層] 関連するスキルを発見",
            "skill_execute": "🔧 [ツール層] スキルを実行",
            "skill_success": "🎛️ [コア層] スキル実行成功",
            "skill_fail": "🎛️ [コア層] スキル実行失敗",
            "explanation_module": "🧠 [推論層] 説明モジュールでレスポンス生成",
            "response_complete": "🧠 [推論層] レスポンス生成完了",
            "session_add_assistant": "💾 [保存層] セッションにアシスタントレスポンスを追加",
            "cache_store": "🎛️ [コア層] レスポンスをキャッシュに保存",
            "complete": "🧠 [完了] レスポンス生成完了",
            "intent_classifying": "🎛️ [コア層] 入力の意図を分類中",
            "intent_result": "🎛️ [コア層] 分類結果",
            "intent_final": "🎛️ [コア層] 最終的な意図",
            "intent_default": "🎛️ [コア層] キーワードが一致しない、デフォルトを使用",
            "router_checking": "🎛️ [コア層] 登録されたルートを確認中",
            "router_found": "🎛️ [コア層] 一致するルートを発見",
            "skill_discovery_start": "🎛️ [コア層] スキル発見を開始",
            "skill_manager_execute": "🔧 [ツール層] スキル実行を試み中",
            "skill_not_found": "🎛️ [コア層] スキルが見つかりません",
            "skill_detail": "🔧 [ツール層] スキル詳細情報",
            "skill_validate_fail": "🎛️ [コア層] パラメーターバリデーション失敗",
            "skill_execute_start": "🔧 [ツール層] パラメーターバリデーション合格、実行開始",
            "skill_execute_success": "🎛️ [コア層] スキル実行成功",
            "skill_execute_error": "🎛️ [コア層] スキル実行エラー",
            "session_add_msg": "💾 [保存層] メッセージを追加",
            "session_trim": "💾 [保存層] 履歴が整理されました",
            "flow_header": "=" * 70,
            
            "step_input": "👤 [ユーザー層] ユーザー入力を受信",
            "step_validation": "🎛️ [コア層] 入力バリデーション合格",
            "step_session": "💾 [保存層] メッセージがセッションに追加されました",
            "step_cache_hit": "🎛️ [コア層] キャッシュヒット、スキップ",
            "step_cache_miss": "🎛️ [コア層] キャッシュミス、続行",
            "step_processing": "🎛️ [コア層] 処理を開始",
            "step_routing": "🎛️ [コア層] タスクルーティングに侵入",
            "step_skill": "🔧 [ツール層] スキルマネージャーに入る",
            "step_explanation": "🧠 [推論層] 説明モジュールを呼び出す",
            "step_complete": "🧠 [完了] 合計時間",
            
            "layer_user": "[ユーザー層]",
            "layer_control": "[コア層]",
            "layer_reasoning": "[推論層]",
            "layer_llm": "[LLM層]",
            "layer_tools": "[ツール層]",
            "layer_storage": "[保存層]",
        }
    }
    
    SUPPORTED_LANGUAGES = {
        "zh": "中文",
        "en": "English", 
        "ko": "한국어",
        "ja": "日本語"
    }
    
    LAYERS = {
        "user": "用户层",
        "control": "控制层",
        "reasoning": "推理层",
        "llm": "LLM层",
        "tools": "工具层",
        "storage": "存储层",
    }
    
    def __init__(self, language: str = "zh"):
        self.language = language if language in self.TRANSLATIONS else "zh"
    
    def t(self, key: str, **kwargs) -> str:
        template = self.TRANSLATIONS.get(self.language, {}).get(
            key, 
            self.TRANSLATIONS["zh"].get(key, key)
        )
        
        if kwargs:
            return template.format(**kwargs)
        return template
    
    def set_language(self, language: str):
        if language in self.TRANSLATIONS:
            self.language = language
    
    def get_language(self) -> str:
        return self.language
    
    @classmethod
    def get_supported_languages(cls) -> Dict[str, str]:
        return cls.SUPPORTED_LANGUAGES.copy()
    
    @classmethod
    def get_layers(cls) -> Dict[str, str]:
        return cls.LAYERS.copy()
    
    @classmethod
    def get_layer_emoji(cls) -> Dict[str, str]:
        return LAYER_EMOJI.copy()


i18n = I18n()


def get_i18n(language: Optional[str] = None) -> I18n:
    if language:
        return I18n(language)
    return i18n

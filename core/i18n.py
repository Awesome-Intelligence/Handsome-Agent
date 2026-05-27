#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Internationalization (i18n) Module for Handsome Agent
Provides multilingual support for logging and system messages.
Supports: Chinese (zh), English (en), Korean (ko), Japanese (ja)
"""

from typing import Dict, Optional


LAYER_EMOJI = {
    "access": "🚪",
    "decision": "🧠",
    "execution": "⚡",
}


class I18n:
    """Internationalization handler for agent messages."""
    
    TRANSLATIONS: Dict[str, Dict[str, str]] = {
        "zh": {
            "flow_start": "🚪 [接入层] 开始处理用户输入",
            "validation_pass": "🧠 [决策层] 输入格式验证通过",
            "session_add": "⚡ [执行层] 添加用户消息到会话",
            "cache_hit": "🧠 [决策层] 缓存命中，跳过处理",
            "cache_miss": "🧠 [决策层] 缓存未命中，执行正常流程",
            "processing_start": "🧠 [决策层] 开始处理请求",
            "routing_enabled": "🧠 [决策层] 启用路由功能，开始意图分类",
            "routing_match": "🧠 [决策层] 找到匹配的路由",
            "routing_no_match": "🧠 [决策层] 未找到匹配的路由，尝试技能执行",
            "skill_enabled": "🧠 [决策层] 启用技能执行，开始意图分类",
            "skill_discovery": "🧠 [决策层] 发现相关技能",
            "skill_execute": "⚡ [执行层] 执行技能",
            "skill_success": "🧠 [决策层] 技能执行成功",
            "skill_fail": "🧠 [决策层] 技能执行失败",
            "explanation_module": "🧠 [决策层] 使用解释模块生成响应",
            "response_complete": "🧠 [决策层] 响应生成完成",
            "session_add_assistant": "⚡ [执行层] 添加助手响应到会话",
            "cache_store": "🧠 [决策层] 存储响应到缓存",
            "complete": "🚪 [完成] 响应生成完成",
            "intent_classifying": "🧠 [决策层] 正在对输入进行意图分类",
            "intent_result": "🧠 [决策层] 分类结果",
            "intent_final": "🧠 [决策层] 最终意图",
            "intent_default": "🧠 [决策层] 未匹配到关键词，默认使用",
            "router_checking": "🧠 [决策层] 检查注册的路由",
            "router_found": "🧠 [决策层] 找到匹配路由",
            "skill_discovery_start": "🧠 [决策层] 开始技能发现",
            "skill_manager_execute": "⚡ [执行层] 尝试执行技能",
            "skill_not_found": "🧠 [决策层] 技能未找到",
            "skill_detail": "⚡ [执行层] 技能详情",
            "skill_validate_fail": "🧠 [决策层] 参数验证失败",
            "skill_execute_start": "⚡ [执行层] 参数验证通过，开始执行",
            "skill_execute_success": "🧠 [决策层] 技能执行成功",
            "skill_execute_error": "🧠 [决策层] 技能执行异常",
            "session_add_msg": "⚡ [执行层] 添加消息",
            "session_trim": "⚡ [执行层] 历史记录已修剪",
            "flow_header": "=" * 70,
            
            "step_input": "🚪 [接入层] 接收用户输入",
            "step_validation": "🧠 [决策层] 输入格式验证通过",
            "step_session": "⚡ [执行层] 消息已添加到会话",
            "step_cache_hit": "🧠 [决策层] 缓存命中，跳过处理",
            "step_cache_miss": "🧠 [决策层] 缓存未命中，执行正常流程",
            "step_processing": "🧠 [决策层] 开始处理请求",
            "step_routing": "🧠 [决策层] 进入任务路由模块",
            "step_skill": "⚡ [执行层] 进入技能管理器",
            "step_explanation": "🧠 [决策层] 调用解释模块处理请求",
            "step_complete": "🚪 [完成] 总耗时",
            
            "layer_access": "[接入层]",
            "layer_decision": "[决策层]",
            "layer_execution": "[执行层]",
        },
        "en": {
            "flow_start": "🚪 [Access Layer] Starting to process user input",
            "validation_pass": "🧠 [Decision Layer] Input validation passed",
            "session_add": "⚡ [Execution Layer] Adding user message to session",
            "cache_hit": "🧠 [Decision Layer] Cache hit, skipping processing",
            "cache_miss": "🧠 [Decision Layer] Cache miss, continuing normal flow",
            "processing_start": "🧠 [Decision Layer] Starting request processing",
            "routing_enabled": "🧠 [Decision Layer] Routing enabled, starting intent classification",
            "routing_match": "🧠 [Decision Layer] Found matching route",
            "routing_no_match": "🧠 [Decision Layer] No matching route found, trying skills",
            "skill_enabled": "🧠 [Decision Layer] Skills enabled, starting intent classification",
            "skill_discovery": "🧠 [Decision Layer] Found relevant skills",
            "skill_execute": "⚡ [Execution Layer] Executing skill",
            "skill_success": "🧠 [Decision Layer] Skill executed successfully",
            "skill_fail": "🧠 [Decision Layer] Skill execution failed",
            "explanation_module": "🧠 [Decision Layer] Using explanation module to generate response",
            "response_complete": "🧠 [Decision Layer] Response generation complete",
            "session_add_assistant": "⚡ [Execution Layer] Adding assistant response to session",
            "cache_store": "🧠 [Decision Layer] Storing response to cache",
            "complete": "🚪 [Complete] Response generation complete",
            "intent_classifying": "🧠 [Decision Layer] Classifying intent for input",
            "intent_result": "🧠 [Decision Layer] Classification result",
            "intent_final": "🧠 [Decision Layer] Final intent",
            "intent_default": "🧠 [Decision Layer] No keywords matched, using default",
            "router_checking": "🧠 [Decision Layer] Checking registered routes",
            "router_found": "🧠 [Decision Layer] Found matching routes",
            "skill_discovery_start": "🧠 [Decision Layer] Starting skill discovery",
            "skill_manager_execute": "⚡ [Execution Layer] Attempting to execute skill",
            "skill_not_found": "🧠 [Decision Layer] Skill not found",
            "skill_detail": "⚡ [Execution Layer] Skill details",
            "skill_validate_fail": "🧠 [Decision Layer] Parameter validation failed",
            "skill_execute_start": "⚡ [Execution Layer] Parameter validation passed, executing",
            "skill_execute_success": "🧠 [Decision Layer] Skill executed successfully",
            "skill_execute_error": "🧠 [Decision Layer] Skill execution error",
            "session_add_msg": "⚡ [Execution Layer] Adding message",
            "session_trim": "⚡ [Execution Layer] History trimmed",
            "flow_header": "=" * 70,
            
            "step_input": "🚪 [Access Layer] Received user input",
            "step_validation": "🧠 [Decision Layer] Input validation passed",
            "step_session": "⚡ [Execution Layer] Message added to session",
            "step_cache_hit": "🧠 [Decision Layer] Cache hit, skipping",
            "step_cache_miss": "🧠 [Decision Layer] Cache miss, continuing",
            "step_processing": "🧠 [Decision Layer] Starting processing",
            "step_routing": "🧠 [Decision Layer] Entering task router",
            "step_skill": "⚡ [Execution Layer] Entering skill manager",
            "step_explanation": "🧠 [Decision Layer] Calling explanation module",
            "step_complete": "🚪 [Complete] Total time",
            
            "layer_access": "[Access Layer]",
            "layer_decision": "[Decision Layer]",
            "layer_execution": "[Execution Layer]",
        },
        "ko": {
            "flow_start": "🚪 [액세스 계층] 사용자 입력 처리 시작",
            "validation_pass": "🧠 [결정 계층] 입력 유효성 검사 통과",
            "session_add": "⚡ [실행 계층] 세션에 사용자 메시지 추가",
            "cache_hit": "🧠 [결정 계층] 캐시 히트, 처리 건너뛰기",
            "cache_miss": "🧠 [결정 계층] 캐시 미스, 정상 처리 계속",
            "processing_start": "🧠 [결정 계층] 요청 처리 시작",
            "routing_enabled": "🧠 [결정 계층] 라우팅 활성화, 의도 분류 시작",
            "routing_match": "🧠 [결정 계층] 매칭 라우트 발견",
            "routing_no_match": "🧠 [결정 계층] 매칭 라우트 없음, 스킬 시도",
            "skill_enabled": "🧠 [결정 계층] 스킬 활성화, 의도 분류 시작",
            "skill_discovery": "🧠 [결정 계층] 관련 스킬 발견",
            "skill_execute": "⚡ [실행 계층] 스킬 실행",
            "skill_success": "🧠 [결정 계층] 스킬 실행 성공",
            "skill_fail": "🧠 [결정 계층] 스킬 실행 실패",
            "explanation_module": "🧠 [결정 계층] 설명 모듈로 응답 생성",
            "response_complete": "🧠 [결정 계층] 응답 생성 완료",
            "session_add_assistant": "⚡ [실행 계층] 세션에 어시스턴트 응답 추가",
            "cache_store": "🧠 [결정 계층] 응답을 캐시에 저장",
            "complete": "🚪 [완료] 응답 생성 완료",
            "intent_classifying": "🧠 [결정 계층] 입력 의도 분류 중",
            "intent_result": "🧠 [결정 계층] 분류 결과",
            "intent_final": "🧠 [결정 계층] 최종 의도",
            "intent_default": "🧠 [결정 계층] 키워드 미매칭, 기본값 사용",
            "router_checking": "🧠 [결정 계층] 등록된 라우트 확인",
            "router_found": "🧠 [결정 계층] 매칭 라우트 발견",
            "skill_discovery_start": "🧠 [결정 계층] 스킬 발견 시작",
            "skill_manager_execute": "⚡ [실행 계층] 스킬 실행 시도",
            "skill_not_found": "🧠 [결정 계층] 스킬을 찾을 수 없음",
            "skill_detail": "⚡ [실행 계층] 스킬 상세정보",
            "skill_validate_fail": "🧠 [결정 계층] 매개변수 유효성 검사 실패",
            "skill_execute_start": "⚡ [실행 계층] 매개변수 유효성 검사 통과, 실행 시작",
            "skill_execute_success": "🧠 [결정 계층] 스킬 실행 성공",
            "skill_execute_error": "🧠 [결정 계층] 스킬 실행 오류",
            "session_add_msg": "⚡ [실행 계층] 메시지 추가",
            "session_trim": "⚡ [실행 계층] 히스토리 정리됨",
            "flow_header": "=" * 70,
            
            "step_input": "🚪 [액세스 계층] 사용자 입력 수신",
            "step_validation": "🧠 [결정 계층] 입력 유효성 검사 통과",
            "step_session": "⚡ [실행 계층] 메시지가 세션에 추가됨",
            "step_cache_hit": "🧠 [결정 계층] 캐시 히트, 건너뛰기",
            "step_cache_miss": "🧠 [결정 계층] 캐시 미스, 계속",
            "step_processing": "🧠 [결정 계층] 처리 시작",
            "step_routing": "🧠 [결정 계층] 태스크 라우터 진입",
            "step_skill": "⚡ [실행 계층] 스킬 매니저 진입",
            "step_explanation": "🧠 [결정 계층] 설명 모듈 호출",
            "step_complete": "🚪 [완료] 총 소요 시간",
            
            "layer_access": "[액세스 계층]",
            "layer_decision": "[결정 계층]",
            "layer_execution": "[실행 계층]",
        },
        "ja": {
            "flow_start": "🚪 [アクセス層] ユーザー入力の処理を開始",
            "validation_pass": "🧠 [決定層] 入力バリデーション合格",
            "session_add": "⚡ [実行層] セッションにユーザーメッセージを追加",
            "cache_hit": "🧠 [決定層] キャッシュヒット、処理をスキップ",
            "cache_miss": "🧠 [決定層] キャッシュミス、通常処理を続行",
            "processing_start": "🧠 [決定層] リクエスト処理を開始",
            "routing_enabled": "🧠 [決定層] ルーティング有効化、意図分類を開始",
            "routing_match": "🧠 [決定層] 一致するルートを発見",
            "routing_no_match": "🧠 [決定層] 一致するルートなし、技能を試す",
            "skill_enabled": "🧠 [決定層] スキル有効化、意図分類を開始",
            "skill_discovery": "🧠 [決定層] 関連するスキルを発見",
            "skill_execute": "⚡ [実行層] スキルを実行",
            "skill_success": "🧠 [決定層] スキル実行成功",
            "skill_fail": "🧠 [決定層] スキル実行失敗",
            "explanation_module": "🧠 [決定層] 説明モジュールでレスポンス生成",
            "response_complete": "🧠 [決定層] レスポンス生成完了",
            "session_add_assistant": "⚡ [実行層] セッションにアシスタントレスポンスを追加",
            "cache_store": "🧠 [決定層] レスポンスをキャッシュに保存",
            "complete": "🚪 [完了] レスポンス生成完了",
            "intent_classifying": "🧠 [決定層] 入力の意図を分類中",
            "intent_result": "🧠 [決定層] 分類結果",
            "intent_final": "🧠 [決定層] 最終的な意図",
            "intent_default": "🧠 [決定層] キーワードが一致しない、デフォルトを使用",
            "router_checking": "🧠 [決定層] 登録されたルートを確認中",
            "router_found": "🧠 [決定層] 一致するルートを発見",
            "skill_discovery_start": "🧠 [決定層] スキル発見を開始",
            "skill_manager_execute": "⚡ [実行層] スキル実行を試み中",
            "skill_not_found": "🧠 [決定層] スキルが見つかりません",
            "skill_detail": "⚡ [実行層] スキル詳細情報",
            "skill_validate_fail": "🧠 [決定層] パラメーターバリデーション失敗",
            "skill_execute_start": "⚡ [実行層] パラメーターバリデーション合格、実行開始",
            "skill_execute_success": "🧠 [決定層] スキル実行成功",
            "skill_execute_error": "🧠 [決定層] スキル実行エラー",
            "session_add_msg": "⚡ [実行層] メッセージを追加",
            "session_trim": "⚡ [実行層] 履歴が整理されました",
            "flow_header": "=" * 70,
            
            "step_input": "🚪 [アクセス層] ユーザー入力を受信",
            "step_validation": "🧠 [決定層] 入力バリデーション合格",
            "step_session": "⚡ [実行層] メッセージがセッションに追加されました",
            "step_cache_hit": "🧠 [決定層] キャッシュヒット、スキップ",
            "step_cache_miss": "🧠 [決定層] キャッシュミス、続行",
            "step_processing": "🧠 [決定層] 処理を開始",
            "step_routing": "🧠 [決定層] タスクルーティングに侵入",
            "step_skill": "⚡ [実行層] スキルマネージャーに入る",
            "step_explanation": "🧠 [決定層] 説明モジュールを呼び出す",
            "step_complete": "🚪 [完了] 合計時間",
            
            "layer_access": "[アクセス層]",
            "layer_decision": "[決定層]",
            "layer_execution": "[実行層]",
        }
    }
    
    SUPPORTED_LANGUAGES = {
        "zh": "中文",
        "en": "English", 
        "ko": "한국어",
        "ja": "日本語"
    }
    
    LAYERS = {
        "access": "接入层",
        "decision": "决策层",
        "execution": "执行层",
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
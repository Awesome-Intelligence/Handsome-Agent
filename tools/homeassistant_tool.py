#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Home Assistant Tool Module

Provides functionality for controlling Home Assistant smart home devices.

Based on Hermes Agent's homeassistant_tool.py implementation.
"""

import json
from typing import Optional, Dict, Any, List

import requests

from common.logging_manager import get_execution_logger
from tools.registry import registry

logger = get_execution_logger("HomeAssistantTool")


def _get_ha_config() -> Optional[Dict[str, str]]:
    """获取 Home Assistant 配置"""
    try:
        from common.config import settings
        
        ha_url = getattr(settings, 'HOMEASSISTANT_URL', None) or getattr(settings, 'HA_URL', None)
        ha_token = getattr(settings, 'HOMEASSISTANT_TOKEN', None) or getattr(settings, 'HA_TOKEN', None)
        
        if ha_url and ha_token:
            return {"url": ha_url.rstrip('/'), "token": ha_token}
    except Exception:
        pass
    
    # 从环境变量获取
    import os
    ha_url = os.environ.get("HOMEASSISTANT_URL") or os.environ.get("HA_URL")
    ha_token = os.environ.get("HOMEASSISTANT_TOKEN") or os.environ.get("HA_TOKEN")
    
    if ha_url and ha_token:
        return {"url": ha_url.rstrip('/'), "token": ha_token}
    
    return None


def _ha_request(method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
    """发送 Home Assistant API 请求"""
    config = _get_ha_config()
    if not config:
        raise RuntimeError("Home Assistant not configured")
    
    url = f"{config['url']}/api{endpoint}"
    headers = {
        "Authorization": f"Bearer {config['token']}",
        "Content-Type": "application/json"
    }
    
    response = requests.request(method, url, headers=headers, json=data, timeout=10)
    response.raise_for_status()
    return response.json()


def ha_list_entities() -> str:
    """
    List all Home Assistant entities.
    
    Returns:
        JSON string with entity list
    """
    try:
        states = _ha_request("GET", "/states")
        
        entities = []
        for state in states:
            entities.append({
                "entity_id": state.get("entity_id"),
                "state": state.get("state"),
                "attributes": state.get("attributes", {}),
                "last_changed": state.get("last_changed"),
                "last_updated": state.get("last_updated")
            })
        
        return json.dumps({
            "success": True,
            "count": len(entities),
            "entities": entities
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Failed to list entities: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "entities": []
        }, ensure_ascii=False)


def ha_get_state(entity_id: str) -> str:
    """
    Get the state of a specific entity.
    
    Args:
        entity_id: The entity ID (e.g., 'light.living_room')
        
    Returns:
        JSON string with entity state
    """
    try:
        state = _ha_request("GET", f"/states/{entity_id}")
        
        return json.dumps({
            "success": True,
            "entity_id": state.get("entity_id"),
            "state": state.get("state"),
            "attributes": state.get("attributes", {}),
            "last_changed": state.get("last_changed"),
            "last_updated": state.get("last_updated")
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Failed to get state for {entity_id}: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "entity_id": entity_id
        }, ensure_ascii=False)


def ha_list_services() -> str:
    """
    List all available Home Assistant services.
    
    Returns:
        JSON string with services list
    """
    try:
        services = _ha_request("GET", "/services")
        
        result = []
        for domain, domain_services in services.items():
            for service, service_data in domain_services.items():
                result.append({
                    "domain": domain,
                    "service": service,
                    "description": service_data.get("description", ""),
                    "fields": service_data.get("fields", {})
                })
        
        return json.dumps({
            "success": True,
            "count": len(result),
            "services": result
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Failed to list services: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "services": []
        }, ensure_ascii=False)


def ha_call_service(
    domain: str,
    service: str,
    entity_id: Optional[str] = None,
    data: Optional[Dict] = None
) -> str:
    """
    Call a Home Assistant service.
    
    Args:
        domain: Service domain (e.g., 'light', 'switch', 'climate')
        service: Service name (e.g., 'turn_on', 'turn_off', 'set_temperature')
        entity_id: Target entity ID (optional if specified in data)
        data: Additional service data
        
    Returns:
        JSON string with service call result
    """
    try:
        payload: Dict[str, Any] = data or {}
        if entity_id:
            payload["entity_id"] = entity_id
        
        result = _ha_request("POST", f"/services/{domain}/{service}", payload)
        
        return json.dumps({
            "success": True,
            "domain": domain,
            "service": service,
            "entity_id": entity_id,
            "result": result
        }, ensure_ascii=False, indent=2)
        
    except Exception as e:
        logger.error(f"Failed to call service {domain}.{service}: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "domain": domain,
            "service": service,
            "entity_id": entity_id
        }, ensure_ascii=False)


def _check_ha_available() -> bool:
    """检查 Home Assistant 是否可用"""
    config = _get_ha_config()
    if not config:
        return False
    
    try:
        _ha_request("GET", "/states")
        return True
    except Exception:
        return False


# Schema definitions
HA_LIST_ENTITIES_SCHEMA = {
    "name": "ha_list_entities",
    "description": "List all entities in Home Assistant with their current states.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}

HA_GET_STATE_SCHEMA = {
    "name": "ha_get_state",
    "description": "Get the current state and attributes of a specific Home Assistant entity.",
    "parameters": {
        "type": "object",
        "properties": {
            "entity_id": {
                "type": "string",
                "description": "The entity ID (e.g., 'light.living_room', 'climate.thermostat')"
            }
        },
        "required": ["entity_id"]
    }
}

HA_LIST_SERVICES_SCHEMA = {
    "name": "ha_list_services",
    "description": "List all available services in Home Assistant.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}

HA_CALL_SERVICE_SCHEMA = {
    "name": "ha_call_service",
    "description": "Call a Home Assistant service to control devices (turn on/off, set brightness, temperature, etc.)",
    "parameters": {
        "type": "object",
        "properties": {
            "domain": {
                "type": "string",
                "description": "Service domain (e.g., 'light', 'switch', 'climate', 'cover', 'fan', 'automation', 'input_boolean')"
            },
            "service": {
                "type": "string",
                "description": "Service name (e.g., 'turn_on', 'turn_off', 'toggle', 'set_temperature', 'open', 'close')"
            },
            "entity_id": {
                "type": "string",
                "description": "Target entity ID (optional if included in data)"
            },
            "data": {
                "type": "object",
                "description": "Additional service data/parameters"
            }
        },
        "required": ["domain", "service"]
    }
}


# Register tools
registry.register(
    name="ha_list_entities",
    toolset="homeassistant",
    schema=HA_LIST_ENTITIES_SCHEMA,
    handler=lambda args, **kw: ha_list_entities(),
    check_fn=_check_ha_available,
    emoji="🏠",
)

registry.register(
    name="ha_get_state",
    toolset="homeassistant",
    schema=HA_GET_STATE_SCHEMA,
    handler=lambda args, **kw: ha_get_state(
        entity_id=args.get("entity_id", "")
    ),
    check_fn=_check_ha_available,
    emoji="🏠",
)

registry.register(
    name="ha_list_services",
    toolset="homeassistant",
    schema=HA_LIST_SERVICES_SCHEMA,
    handler=lambda args, **kw: ha_list_services(),
    check_fn=_check_ha_available,
    emoji="🏠",
)

registry.register(
    name="ha_call_service",
    toolset="homeassistant",
    schema=HA_CALL_SERVICE_SCHEMA,
    handler=lambda args, **kw: ha_call_service(
        domain=args.get("domain", ""),
        service=args.get("service", ""),
        entity_id=args.get("entity_id"),
        data=args.get("data")
    ),
    check_fn=_check_ha_available,
    emoji="🏠",
)

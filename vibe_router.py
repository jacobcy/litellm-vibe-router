#!/usr/bin/env python3
"""
LiteLLM Intelligent Router Plugin
实现智能路由 + 限流回落 + 简单任务降级

路由逻辑：
1. 简单任务 (复杂度 < 50): 直接路由到轻量级模型
2. 复杂任务 (复杂度 >= 50): 使用默认模型
3. 限流/失败: LiteLLM router 自动 fallback 到下一级模型

Fallback 链 (chat-auto 为例):
   openai/gpt-5 (主模型) → gpt-5 (限流回落) → gpt-5-mini (最终兜底)
"""

import sys
import time
from typing import Optional, Dict, Any, List, Literal, Union

# Initialize logging immediately
def _log(message: str, level: str = "INFO"):
    """Thread-safe logging to stderr"""
    timestamp = time.strftime("%H:%M:%S")
    sys.stderr.write(f"[{timestamp}] [VIBE-ROUTER] [{level}] {message}\n")
    sys.stderr.flush()

_log("=" * 70)
_log("Plugin module loading...")
_log("=" * 70)

try:
    from litellm.integrations.custom_logger import CustomLogger
    from litellm.proxy.proxy_server import UserAPIKeyAuth, DualCache
    import litellm
    _log("✓ LiteLLM imports successful")
except ImportError as e:
    _log(f"✗ Import failed: {e}", "ERROR")
    raise


class VibeIntelligentRouter(CustomLogger):
    """
    智能路由器：
    - 处理所有虚拟模型 (chat-auto, codex-auto, claude-auto)
    - 根据复杂度判定简单任务
    - 简单任务直接路由到轻量级模型
    - LiteLLM router 处理限流回落
    """

    # 简单任务直接路由的目标模型
    SIMPLE_TASK_TARGETS = {
        "chat-auto": "gpt-5-mini",
        "codex-auto": "gpt-5.1-codex-mini",
        "claude-auto": "claude-haiku-4-5"
    }

    def __init__(self):
        super().__init__()
        _log("Initializing VibeIntelligentRouter...")

        # 简单任务指标
        self.simple_indicators = {
            # Unix commands
            "ls", "cat", "pwd", "cd", "grep", "find", "echo", "cp", "mv", "rm",
            # Greetings
            "hi", "hello", "hey", "你好", "nihao",
            # Simple words
            "test", "ping", "status", "help"
        }

        # 复杂任务指标
        self.complex_indicators = {
            "implement", "algorithm", "architecture", "analyze", "design",
            "refactor", "optimize", "debug", "philosophical", "comprehensive",
            "concurrent", "distributed", "recursive"
        }

        _log(f"Supported virtual models: {list(self.SIMPLE_TASK_TARGETS.keys())}")
        _log("✓ Router initialized successfully")

    def _calculate_complexity(self, messages: List[Dict]) -> int:
        """
        计算消息复杂度评分
        分数越高 = 越复杂
        """
        if not messages:
            return 0

        score = 0

        # 分析最后一条消息 (用户的请求)
        last_msg = messages[-1]
        content = str(last_msg.get("content", "")).lower()

        # 因子 1: 消息长度 (越长越复杂)
        content_length = len(content.strip())
        score += min(content_length, 200)  # 上限 200

        # 因子 2: 简单指标 (降低分数)
        simple_match = sum(1 for indicator in self.simple_indicators if indicator in content)
        if simple_match > 0:
            score -= 100 * simple_match

        # 因子 3: 复杂指标 (增加分数)
        complex_match = sum(1 for indicator in self.complex_indicators if indicator in content)
        if complex_match > 0:
            score += 150 * complex_match

        # 因子 4: 代码块 (技术内容 = 复杂)
        if "```" in content or "def " in content or "function " in content:
            score += 100

        # 因子 5: 多句子 (详细请求 = 复杂)
        sentence_count = content.count('.') + content.count('?') + content.count('!')
        if sentence_count > 2:
            score += 50

        # 因子 6: 对话历史 (长对话 = 复杂)
        if len(messages) > 5:
            score += 30

        return max(0, score)  # 确保非负

    async def async_pre_call_hook(
        self,
        user_api_key_dict: UserAPIKeyAuth,
        cache: DualCache,
        data: Dict,
        call_type: Literal[
            "completion",
            "text_completion",
            "embeddings",
            "image_generation",
            "moderation",
            "audio_transcription"
        ],
    ) -> Optional[Union[Dict, Exception]]:
        """
        核心 Hook：在模型别名映射之后、路由器解析之前执行

        执行顺序 (来自 LiteLLM 源码):
        1. 虚拟 key 验证
        2. 模型别名映射 (litellm.model_alias_map)
        3. → async_pre_call_hook (我们在这里) ←
        4. 路由器模型解析
        5. 模型验证
        6. LiteLLM API 调用
        """
        try:
            _log(f"Hook triggered - call_type={call_type}")

            # 安全检查
            if data is None:
                _log("WARNING: data is None, returning as-is", "WARN")
                return data

            # 获取当前模型
            original_model = data.get("model")
            _log(f"Original model: {original_model}")

            # 只处理虚拟模型
            if original_model not in self.SIMPLE_TASK_TARGETS:
                _log("Not a virtual model, passing through")
                return data

            # 提取消息
            messages = data.get("messages", [])
            if not messages:
                _log("No messages found, using default model", "WARN")
                return data

            # 计算复杂度
            complexity_score = self._calculate_complexity(messages)

            # 决策阈值
            COMPLEXITY_THRESHOLD = 50
            is_simple = complexity_score < COMPLEXITY_THRESHOLD

            # 简单任务：直接路由到轻量级模型
            if is_simple:
                target_model = self.SIMPLE_TASK_TARGETS[original_model]
                data["model"] = target_model

                # 添加元数据用于可观察性
                if "metadata" not in data:
                    data["metadata"] = {}
                data["metadata"]["virtual_model"] = original_model
                data["metadata"]["routed_model"] = target_model
                data["metadata"]["complexity_score"] = complexity_score
                data["metadata"]["routing_reason"] = "simple_task"

                _log("=" * 70)
                _log(f"✓ SIMPLE TASK ROUTING:")
                _log(f"  Virtual Model:    {original_model}")
                _log(f"  Target Model:      {target_model}")
                _log(f"  Complexity Score:  {complexity_score}")
                _log(f"  Decision:          SIMPLE → Lightweight Model")
                _log(f"  Message Preview:   {messages[-1].get('content', '')[:60]}...")
                _log("=" * 70)
            else:
                # 复杂任务：使用默认模型，LiteLLM router 会处理限流回落
                _log(f"Complex task (score={complexity_score}), using default model for fallback chain")

                # 添加元数据
                if "metadata" not in data:
                    data["metadata"] = {}
                data["metadata"]["virtual_model"] = original_model
                data["metadata"]["complexity_score"] = complexity_score
                data["metadata"]["routing_reason"] = "complex_task"

            # 关键：必须返回修改后的 data 对象
            return data

        except Exception as e:
            _log(f"ERROR in async_pre_call_hook: {str(e)}", "ERROR")
            import traceback
            _log(traceback.format_exc(), "ERROR")
            # 返回未修改的 data 以防止破坏请求
            return data

    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        """记录成功的路由"""
        try:
            model = kwargs.get("model", "unknown")
            metadata = kwargs.get("metadata", {})
            virtual_model = metadata.get("virtual_model")

            if virtual_model:
                duration = (end_time - start_time).total_seconds()
                routing_reason = metadata.get("routing_reason", "default")
                _log(f"✓ SUCCESS: {virtual_model} -> {model} ({duration:.2f}s, reason={routing_reason})")
        except Exception as e:
            _log(f"Error in success logger: {e}", "ERROR")

    async def async_log_failure_event(self, kwargs, response_obj, start_time, end_time):
        """记录失败的路由"""
        try:
            model = kwargs.get("model", "unknown")
            metadata = kwargs.get("metadata", {})
            virtual_model = metadata.get("virtual_model", model)
            error = str(response_obj) if response_obj else "unknown"

            _log(f"✗ FAILURE: {virtual_model} -> {model}", "ERROR")
            _log(f"  Error: {error[:200]}", "ERROR")
            _log(f"  (LiteLLM router will retry with fallback model if available)", "ERROR")
        except Exception as e:
            _log(f"Error in failure logger: {e}", "ERROR")


# Create singleton instance
_log("-" * 70)
_log("Creating router instance...")
router_instance = VibeIntelligentRouter()
_log("✓ router_instance created and ready")
_log("-" * 70)

# Export for LiteLLM callback system
proxy_handler_instance = router_instance
callback_handler = router_instance

_log("Plugin module loaded successfully ✓")

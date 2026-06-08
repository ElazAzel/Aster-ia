from __future__ import annotations

from functools import lru_cache

from asterion_api.config import Settings, get_settings
from asterion_api.services.agent_executor import AgentExecutor
from asterion_api.services.agent_registry import AgentRegistry
from asterion_api.services.agent_sandbox import AgentSandbox, TaskSimulator
from asterion_api.services.chat_service import ChatService
from asterion_api.services.comfyui_service import ComfyUIService
from asterion_api.services.contradiction_finder import ContradictionFinder
from asterion_api.services.deep_research import SupervisorAgent
from asterion_api.services.memory_ledger import MemoryLedger
from asterion_api.services.model_router import ModelRouter
from asterion_api.services.ollama_service import OllamaService
from asterion_api.services.plugin_manager import PluginManager
from asterion_api.services.benchmark_service import BenchmarkService
from asterion_api.services.privacy_analyzer import PrivacyAnalyzer
from asterion_api.services.rag import DocumentIndexer
from asterion_api.services.vllm_service import VllmService
from asterion_api.services.voice_service import VoiceService
from asterion_api.services.workflow_runner import WorkflowRunner
from asterion_api.storage.encrypted_sqlite import EncryptedSQLiteStore


@lru_cache(maxsize=1)
def get_store() -> EncryptedSQLiteStore:
    return EncryptedSQLiteStore(get_settings())


@lru_cache(maxsize=1)
def get_ollama_service() -> OllamaService:
    return OllamaService(get_settings())


@lru_cache(maxsize=1)
def get_chat_service() -> ChatService:
    settings: Settings = get_settings()
    return ChatService(
        settings=settings,
        ollama=get_ollama_service(),
        store=get_store(),
        vllm=get_vllm_service(),
    )


@lru_cache(maxsize=1)
def get_privacy_analyzer() -> PrivacyAnalyzer:
    return PrivacyAnalyzer()


@lru_cache(maxsize=1)
def get_model_router() -> ModelRouter:
    return ModelRouter()


@lru_cache(maxsize=1)
def get_memory_ledger() -> MemoryLedger:
    return MemoryLedger(get_store(), get_privacy_analyzer())


@lru_cache(maxsize=1)
def get_document_indexer() -> DocumentIndexer:
    return DocumentIndexer(get_settings(), get_ollama_service())


@lru_cache(maxsize=1)
def get_supervisor_agent() -> SupervisorAgent:
    return SupervisorAgent(get_privacy_analyzer(), get_settings())


@lru_cache(maxsize=1)
def get_contradiction_finder() -> ContradictionFinder:
    return ContradictionFinder(get_ollama_service())


@lru_cache(maxsize=1)
def get_task_simulator() -> TaskSimulator:
    return TaskSimulator()


@lru_cache(maxsize=1)
def get_agent_sandbox() -> AgentSandbox:
    return AgentSandbox()


@lru_cache(maxsize=1)
def get_agent_registry() -> AgentRegistry:
    return AgentRegistry()


@lru_cache(maxsize=1)
def get_agent_executor() -> AgentExecutor:
    return AgentExecutor(get_store(), get_agent_registry())


@lru_cache(maxsize=1)
def get_comfyui_service() -> ComfyUIService:
    return ComfyUIService(get_settings())


@lru_cache(maxsize=1)
def get_voice_service() -> VoiceService:
    return VoiceService()


@lru_cache(maxsize=1)
def get_workflow_runner() -> WorkflowRunner:
    return WorkflowRunner(get_store())


@lru_cache(maxsize=1)
def get_plugin_manager() -> PluginManager:
    return PluginManager(get_settings())


@lru_cache(maxsize=1)
def _benchmark_service_singleton() -> BenchmarkService:
    return BenchmarkService(ollama_base_url=get_settings().ollama_base_url)


def get_benchmark_service() -> BenchmarkService:
    return _benchmark_service_singleton()


@lru_cache(maxsize=1)
def _vllm_service_singleton() -> VllmService:
    return VllmService()


def get_vllm_service() -> VllmService:
    return _vllm_service_singleton()

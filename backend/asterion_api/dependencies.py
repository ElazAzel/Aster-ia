from __future__ import annotations

from functools import lru_cache

from asterion_api.config import Settings, get_settings
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
from asterion_api.services.privacy_analyzer import PrivacyAnalyzer
from asterion_api.services.rag import DocumentIndexer
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
    return SupervisorAgent(get_privacy_analyzer())


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
def get_comfyui_service() -> ComfyUIService:
    return ComfyUIService()


@lru_cache(maxsize=1)
def get_workflow_runner() -> WorkflowRunner:
    return WorkflowRunner()


@lru_cache(maxsize=1)
def get_plugin_manager() -> PluginManager:
    return PluginManager(get_settings())

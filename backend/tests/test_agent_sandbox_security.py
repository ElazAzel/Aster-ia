import pytest
from asterion_api.schemas import AgentPermissions
from asterion_api.services.agent_sandbox import AgentSandbox


def _sandbox():
    return AgentSandbox()


def test_block_shell_import():
    sandbox = _sandbox()
    perms = AgentPermissions(network=False, shell=False, allowed_folders=[])
    with pytest.raises(PermissionError, match="shell blocked"):
        sandbox._validate_code("import subprocess", perms)


def test_block_shell_from_import():
    sandbox = _sandbox()
    perms = AgentPermissions(network=False, shell=False, allowed_folders=[])
    with pytest.raises(PermissionError, match="shell blocked"):
        sandbox._validate_code("from os import system", perms)


def test_block_network_import():
    sandbox = _sandbox()
    perms = AgentPermissions(network=False, shell=False, allowed_folders=[])
    with pytest.raises(PermissionError, match="network blocked"):
        sandbox._validate_code("import httpx", perms)


def test_block_dunder_import():
    sandbox = _sandbox()
    perms = AgentPermissions(network=False, shell=False, allowed_folders=[])
    with pytest.raises(PermissionError, match="shell blocked"):
        sandbox._validate_code('__import__("subprocess")', perms)


def test_block_eval():
    sandbox = _sandbox()
    perms = AgentPermissions(network=False, shell=False, allowed_folders=[])
    with pytest.raises(PermissionError, match="shell blocked"):
        sandbox._validate_code('eval("__import__(\'os\')")', perms)


def test_allow_harmless_code():
    sandbox = _sandbox()
    perms = AgentPermissions(network=False, shell=False, allowed_folders=[])
    sandbox._validate_code("x = 1\ny = x + 2\nprint(y)", perms)


def test_syntax_error_raises():
    sandbox = _sandbox()
    perms = AgentPermissions(network=False, shell=False, allowed_folders=[])
    with pytest.raises(PermissionError, match="Syntax error"):
        sandbox._validate_code("def (", perms)


def test_network_allowed_when_permitted():
    sandbox = _sandbox()
    perms = AgentPermissions(network=True, shell=False, allowed_folders=[])
    sandbox._validate_code("import httpx", perms)


def test_shell_allowed_when_permitted():
    sandbox = _sandbox()
    perms = AgentPermissions(network=False, shell=True, allowed_folders=[])
    sandbox._validate_code("import subprocess", perms)

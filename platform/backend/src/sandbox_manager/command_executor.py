"""Stub CommandExecutor."""


class CommandExecutor:
    @staticmethod
    def execute(container_name: str, command: str, timeout: int = 300):
        return {"success": True, "output": "", "error": ""}

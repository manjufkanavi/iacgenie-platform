import re

import os

from typing import Dict, Any, List

import logging

logger = logging.getLogger(__name__)


class SecretsScanner:
    """Scans for and handles secrets in HCL code and workspace files."""

    def __init__(self) -> None:
        self.secret_patterns = self._load_secret_patterns()
        self.redaction_patterns = self._load_redaction_patterns()

    def _load_secret_patterns(self) -> List[Dict[str, Any]]:
        """Load patterns for detecting secrets."""
        return [
            {
                "name": "AWS Access Key ID",
                "pattern": r"AKIA[0-9A-Z]{16}",
                "severity": "critical",
                "description": "AWS access key ID detected",
            },
            {
                "name": "AWS Secret Access Key",
                "pattern": r"[a-zA-Z0-9/+=]{40}",
                "severity": "critical",
                "description": "Potential AWS secret access key detected",
            },
            {
                "name": "Generic API Key",
                "pattern": r'api[_-]?key\s*=\s*["\'][a-zA-Z0-9]{32,}["\']',
                "severity": "high",
                "description": "Generic API key pattern detected",
            },
            {
                "name": "Password Assignment",
                "pattern": r'password\s*=\s*["\'][^"\']{8,}["\']',
                "severity": "high",
                "description": "Password assignment detected",
            },
            {
                "name": "Private Key",
                "pattern": r"-----BEGIN (RSA|DSA|EC|OPENSSH|PGP) PRIVATE KEY-----",
                "severity": "critical",
                "description": "Private key block detected",
            },
            {
                "name": "Bearer Token",
                "pattern": r"bearer\s+[a-zA-Z0-9\-_=]+\.[a-zA-Z0-9\-_=]+\.[a-zA-Z0-9\-_=]+",
                "severity": "critical",
                "description": "Bearer token detected",
            },
            {
                "name": "Basic Auth",
                "pattern": r"[Bb]asic\s+[A-Za-z0-9+/=]{50,}",
                "severity": "high",
                "description": "Basic authentication token detected",
            },
        ]

    def _load_redaction_patterns(self) -> List[Dict[str, Any]]:
        """Load patterns for redacting secrets in logs."""
        return [
            {
                "name": "AWS Keys",
                "pattern": r"(AKIA[0-9A-Z]{16}|[a-zA-Z0-9/+=]{40})",
                "replacement": "[REDACTED_AWS_KEY]",
            },
            {
                "name": "API Keys",
                "pattern": r'api[_-]?key\s*=\s*["\'][^"\']+["\']',
                "replacement": 'api_key="[REDACTED_API_KEY]"',
            },
            {
                "name": "Passwords",
                "pattern": r'password\s*=\s*["\'][^"\']+["\']',
                "replacement": 'password="[REDACTED_PASSWORD]"',
            },
            {
                "name": "Tokens",
                "pattern": r'(token|secret)\s*=\s*["\'][^"\']+["\']',
                "replacement": '\\1="[REDACTED_TOKEN]"',
            },
        ]

    def scan_hcl_code(self, hcl_code: str) -> Dict[str, Any]:
        """
        Scan HCL code for secrets.
        Args:
            hcl_code: HCL code to scan
        Returns:
            Dictionary with scan results
        """
        findings = []
        for pattern in self.secret_patterns:
            matches = re.finditer(pattern["pattern"], hcl_code, re.IGNORECASE)
            for match in matches:
                findings.append(
                    {
                        "type": pattern["name"],
                        "severity": pattern["severity"],
                        "description": pattern["description"],
                        "match": match.group(),
                        "position": {
                            "start": match.start(),
                            "end": match.end(),
                            "line": hcl_code[: match.start()].count("\n") + 1,
                        },
                        "context": self._get_match_context(hcl_code, match),
                    }
                )
        return {
            "success": True,
            "findings": findings,
            "critical_count": len([f for f in findings if f["severity"] == "critical"]),
            "high_count": len([f for f in findings if f["severity"] == "high"]),
            "total_findings": len(findings),
        }

    def _get_match_context(self, hcl_code: str, match: re.Match) -> str:
        """Get context around a secret match."""
        start_pos = max(0, match.start() - 50)
        end_pos = min(len(hcl_code), match.end() + 50)
        lines = hcl_code[start_pos:end_pos].split("\n")
        context_lines = []
        for i, line in enumerate(lines):
            line_num = hcl_code[:start_pos].count("\n") + i + 1
            context_lines.append(f"{line_num:4d}: {line}")
        return "\n".join(context_lines)

    def scan_workspace_files(self, workspace_path: str) -> Dict[str, Any]:
        """
        Scan all files in a workspace for secrets.
        Args:
            workspace_path: Path to workspace directory
        Returns:
            Dictionary with scan results
        """
        if not os.path.exists(workspace_path):
            return {"success": False, "error": f"Workspace not found: {workspace_path}"}
        all_findings = []
        scanned_files = 0
        files_with_findings = 0
        for root, dirs, files in os.walk(workspace_path):
            for file in files:
                file_path = os.path.join(root, file)
                scanned_files += 1
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                        result = self.scan_hcl_code(content)
                        if result["findings"]:
                            files_with_findings += 1
                            for finding in result["findings"]:
                                finding["file"] = file_path
                                finding["relative_path"] = os.path.relpath(
                                    file_path, workspace_path
                                )
                            all_findings.extend(result["findings"])
                except Exception as e:
                    self.log_message(
                        f"Failed to scan file {file_path}: {str(e)}", "warning"
                    )
                    continue
        return {
            "success": True,
            "findings": all_findings,
            "scanned_files": scanned_files,
            "files_with_findings": files_with_findings,
            "critical_count": len(
                [f for f in all_findings if f["severity"] == "critical"]
            ),
            "high_count": len([f for f in all_findings if f["severity"] == "high"]),
            "total_findings": len(all_findings),
        }

    def redact_secrets(self, text: str) -> str:
        """
        Redact secrets from text (for logging).
        Args:
            text: Text to redact
        Returns:
            Redacted text
        """
        redacted_text = text
        for pattern in self.redaction_patterns:
            redacted_text = re.sub(
                pattern["pattern"],
                pattern["replacement"],
                redacted_text,
                flags=re.IGNORECASE,
            )
        return redacted_text

    def handle_secret_violation(
        self, findings: List[Dict[str, Any]], session_id: str
    ) -> Dict[str, Any]:
        """
        Handle detected secret violations.
        Args:
            findings: List of secret findings
            session_id: Pipeline session ID
        Returns:
            Dictionary with handling result
        """
        if not findings:
            return {"success": True, "message": "No secret violations to handle"}
        # Classify severity
        has_critical = any(f["severity"] == "critical" for f in findings)
        has_high = any(f["severity"] == "high" for f in findings)
        # Determine action based on severity
        actions = []
        if has_critical:
            actions.append("IMMEDIATE_ESCALATION")
            actions.append("PIPELINE_ABORT")
            actions.append("NOTIFY_SECURITY_TEAM")
        elif has_high:
            actions.append("ESCALATION")
            actions.append("HUMAN_REVIEW_REQUIRED")
        else:
            actions.append("LOG_WARNING")
        # Generate report
        report = self._generate_secrets_report(findings)
        return {
            "success": True,
            "actions_required": actions,
            "severity": "critical" if has_critical else "high",
            "report": report,
            "message": f"Secret violation detected - {len(findings)} findings",
        }

    def _generate_secrets_report(
        self, findings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate a detailed report of secret findings."""
        report: Dict[str, Any] = {
            "summary": {
                "total_findings": len(findings),
                "critical": len([f for f in findings if f["severity"] == "critical"]),
                "high": len([f for f in findings if f["severity"] == "high"]),
                "files_affected": len(set(f.get("file", "unknown") for f in findings)),
            },
            "findings_by_type": {},
            "findings_by_file": {},
            "sample_findings": [],
        }
        # Group findings by type
        for finding in findings:
            finding_type = finding["type"]
            if finding_type not in report["findings_by_type"]:
                report["findings_by_type"][finding_type] = 0
            report["findings_by_type"][finding_type] += 1
            # Add sample findings (first 5 of each type)
            if finding_type not in [f["type"] for f in report["sample_findings"]]:
                report["sample_findings"].append(
                    {
                        "type": finding["type"],
                        "severity": finding["severity"],
                        "description": finding["description"],
                        "context": finding.get("context", "No context available"),
                    }
                )
                if len(report["sample_findings"]) >= 5:
                    break
        # Group findings by file
        for finding in findings:
            file_path = finding.get("file", "unknown")
            if file_path not in report["findings_by_file"]:
                report["findings_by_file"][file_path] = 0
            report["findings_by_file"][file_path] += 1
        return report

    def add_custom_pattern(
        self, pattern_name: str, regex_pattern: str, severity: str
    ) -> Dict[str, Any]:
        """
        Add a custom secret detection pattern.
        Args:
            pattern_name: Name of the pattern
            regex_pattern: Regular expression pattern
            severity: Severity level (critical, high, medium, low)
        Returns:
            Dictionary with addition result
        """
        try:
            # Validate the regex pattern
            re.compile(regex_pattern)
            self.secret_patterns.append(
                {
                    "name": pattern_name,
                    "pattern": regex_pattern,
                    "severity": severity,
                    "description": f"Custom pattern: {pattern_name}",
                }
            )
            self.log_message(f"Added custom secret pattern: {pattern_name}")
            return {"success": True, "message": "Custom pattern added successfully"}
        except re.error as e:
            return {"success": False, "error": f"Invalid regular expression: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def validate_no_secrets(self, hcl_code: str) -> Dict[str, Any]:
        """
        Validate that HCL code contains no secrets.
        Args:
            hcl_code: HCL code to validate
        Returns:
            Dictionary with validation result
        """
        result = self.scan_hcl_code(hcl_code)
        if result["findings"]:
            return {
                "success": False,
                "error": f"Secrets detected: {result['total_findings']} findings",
                "findings": result["findings"],
                "severity": "critical" if result["critical_count"] > 0 else "high",
            }
        return {"success": True, "message": "No secrets detected"}

    def log_message(self, message: str, level: str = "info") -> None:
        """Log a message with secrets scanner context."""
        context = {
            "component": "secrets_scanner",
            "active_patterns": len(self.secret_patterns),
        }
        if level == "info":
            logger.info(message, extra=context)
        elif level == "warning":
            logger.warning(message, extra=context)
        elif level == "error":
            logger.error(message, extra=context)
        else:
            logger.debug(message, extra=context)


# Example usage and integration


def create_secrets_scanner_with_custom_patterns() -> SecretsScanner:
    """Create a secrets scanner with additional custom patterns."""
    scanner = SecretsScanner()
    # Add custom patterns for specific use cases
    scanner.add_custom_pattern("GitHub Token", r"ghp_[a-zA-Z0-9]{36}", "critical")
    scanner.add_custom_pattern(
        "Slack Token",
        r"xox[baprs]-[0-9]{10,}-[0-9]{10,}-[0-9]{10,}-[a-z0-9]{32}",
        "high",
    )
    return scanner


def scan_and_handle_secrets_workflow(hcl_code: str, session_id: str) -> Dict[str, Any]:
    """
    Complete workflow for scanning and handling secrets.
    Args:
        hcl_code: HCL code to scan
        session_id: Pipeline session ID
    Returns:
        Dictionary with workflow result
    """
    scanner = SecretsScanner()
    # Step 1: Scan for secrets
    scan_result = scanner.scan_hcl_code(hcl_code)
    if not scan_result["findings"]:
        return {"success": True, "message": "No secrets detected", "status": "clean"}
    # Step 2: Handle violations
    handling_result = scanner.handle_secret_violation(
        scan_result["findings"], session_id
    )
    # Step 3: Generate redacted version for logging
    redacted_code = scanner.redact_secrets(hcl_code)
    return {
        "success": False,
        "status": "violations_found",
        "scan_result": scan_result,
        "handling_result": handling_result,
        "redacted_code": redacted_code,
        "message": f"Secret violations detected: {scan_result['total_findings']} findings",
    }

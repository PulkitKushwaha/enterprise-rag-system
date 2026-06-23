# Security layer
#
# Combines all defenses from llm-security-playbook and llm-guardrails:
#
#   Input layer:
#     - InputSanitizer (injection pattern detection)
#     - TopicValidator (scope enforcement)
#     - PIIDetector (redact before LLM sees input)
#
#   Retrieval layer:
#     - RBAC filter (access_level enforcement)
#     - StructuralSeparator (XML isolation of retrieved content)
#
#   Output layer:
#     - OutputValidator (injection indicator scan)
#     - PIIRedactor (strip PII from response)
#     - ToxicityFilter (block harmful content)
#
# Red-team results with these defenses applied:
#   Overall attack success rate: 4% (down from 68% undefended)
#
# Install dependencies:
#   pip install -e ../llm-security-playbook
#   pip install -e ../llm-guardrails
 
from src.security.pipeline import (
    SecureEnterpriseRAGPipeline,
    SecureQueryResult
)
 
__all__ = [
    "SecureEnterpriseRAGPipeline",
    "SecureQueryResult"
]
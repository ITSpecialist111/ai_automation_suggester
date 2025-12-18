"""Constants for the AI Automation Suggester integration."""

# ─────────────────────────────────────────────────────────────
# Core
# ─────────────────────────────────────────────────────────────
DOMAIN           = "ai_automation_suggester"
PLATFORMS        = ["sensor"]
CONFIG_VERSION   = 2  # config‑entry version (used by async_migrate_entry)
INTEGRATION_NAME = "AI Automation Suggester"

# ─────────────────────────────────────────────────────────────
# Token budgeting
# ─────────────────────────────────────────────────────────────
# Single legacy knob (kept for backward compatibility)
CONF_MAX_TOKENS = "max_tokens"
DEFAULT_MAX_TOKENS = 500  # legacy default – used for both budgets if new keys absent

# New, separate knobs (Issue #91)
CONF_MAX_INPUT_TOKENS = "max_input_tokens"  # how much of the prompt we keep
CONF_MAX_OUTPUT_TOKENS = "max_output_tokens"  # how long the AI response may be

DEFAULT_MAX_INPUT_TOKENS = DEFAULT_MAX_TOKENS
DEFAULT_MAX_OUTPUT_TOKENS = DEFAULT_MAX_TOKENS

DEFAULT_TEMPERATURE = 0.7

DEFAULT_TIMEOUT = 30  # seconds

# ─────────────────────────────────────────────────────────────
# Provider‑selection key
# ─────────────────────────────────────────────────────────────
CONF_PROVIDER = "provider"

# ─────────────────────────────────────────────────────────────
# Provider‑specific keys
# ─────────────────────────────────────────────────────────────
# Common
CONF_API_KEY = "api_key"
CONF_MODEL = "model"
CONF_TEMPERATURE = "temperature"
CONF_TIMEOUT = "timeout"

# OpenAI Azure
CONF_OPENAI_AZURE_DEPLOYMENT_ID = "openai_azure_deployment_id"
CONF_OPENAI_AZURE_API_VERSION = "openai_azure_api_version"
CONF_OPENAI_AZURE_ENDPOINT = "openai_azure_endpoint"

# Anthropic
VERSION_ANTHROPIC = "2023-06-01"

# LocalAI
CONF_LOCALAI_IP_ADDRESS = "localai_ip"
CONF_LOCALAI_PORT = "localai_port"
CONF_LOCALAI_HTTPS = "localai_https"

# Ollama
CONF_OLLAMA_IP_ADDRESS = "ollama_ip"
CONF_OLLAMA_PORT = "ollama_port"
CONF_OLLAMA_HTTPS = "ollama_https"
CONF_OLLAMA_DISABLE_THINK = "ollama_disable_think"

# Google
CONF_GOOGLE_THINKING_MODE = "google_thinking_mode"
CONF_GOOGLE_THINKING_BUDGET = "google_thinking_budget"
CONF_GOOGLE_ENABLE_SEARCH = "google_search"

# Open Web UI
CONF_OPENWEBUI_IP_ADDRESS = "openwebui_ip"
CONF_OPENWEBUI_PORT = "openwebui_port"
CONF_OPENWEBUI_HTTPS = "openwebui_https"
CONF_OPENWEBUI_DISABLE_THINK = "openwebui_disable_think"

# Custom OpenAI
CONF_CUSTOM_OPENAI_ENDPOINT = "custom_openai_endpoint"

# Mistral AI
MISTRAL_MODELS = [
    "mistral-tiny",
    "mistral-small",
    "mistral-medium",
    "mistral-large",
]

# OpenRouter
CONF_OPENROUTER_REASONING_MAX_TOKENS = "openrouter_reasoning_max_tokens"

# Generic OpenAI
CONF_GENERIC_OPENAI_ENDPOINT = "generic_openai_api_endpoint"
CONF_GENERIC_OPENAI_VALIDATION_ENDPOINT = "generic_openai_validation_endpoint"
CONF_GENERIC_OPENAI_ENABLE_VALIDATION = "generic_openai_enable_validation"

# ─────────────────────────────────────────────────────────────
# Model defaults per provider
# ─────────────────────────────────────────────────────────────
DEFAULT_MODELS = {
    "OpenAI": "gpt-4o-mini",
    "OpenAI Azure": "gpt-4o-mini",
    "Anthropic": "claude-3-7-sonnet-latest",
    "Google": "gemini-2.0-flash",
    "Groq": "llama3-8b-8192",
    "LocalAI": "llama3",
    "Ollama": "llama2",
    "Custom OpenAI": "gpt-3.5-turbo",
    "Mistral AI": "mistral-medium",
    "Perplexity AI": "sonar",
    "OpenRouter": "meta-llama/llama-4-maverick:free",
    "Generic OpenAI": "gpt-3.5-turbo",
    "Codestral": "codestral-latest",
    "Venice AI": "venice-uncensored",
    "Open Web UI": "llama2",
    "ZhipuAI": "glm-4.5-flash",
}

# ─────────────────────────────────────────────────────────────
# Service & attribute names
# ─────────────────────────────────────────────────────────────
ATTR_PROVIDER_CONFIG = "provider_config"
ATTR_CUSTOM_PROMPT = "custom_prompt"
SERVICE_GENERATE_SUGGESTIONS = "generate_suggestions"
SERVICE_ANALYZE_ERROR = "analyze_error"
ATTR_INCLUDE_ENTITY_DETAILS = "include_entity_details"

# ─────────────────────────────────────────────────────────────
# Provider‑status sensor values
# ─────────────────────────────────────────────────────────────
PROVIDER_STATUS_CONNECTED = "connected"
PROVIDER_STATUS_DISCONNECTED = "disconnected"
PROVIDER_STATUS_ERROR        = "error"
PROVIDER_STATUS_INITIALIZING = "initializing"

# ─────────────────────────────────────────────────────────────
# REST endpoints
# ─────────────────────────────────────────────────────────────
ENDPOINT_OPENAI = "https://api.openai.com/v1/chat/completions"
ENDPOINT_OPENAI_AZURE = "https://{endpoint}/openai/deployments/{deployment-id}/chat/completions?api-version={api_version}"
ENDPOINT_ANTHROPIC = "https://api.anthropic.com/v1/messages"
ENDPOINT_GOOGLE = "https://generativelanguage.googleapis.com/v1beta2/models/{model}:generateText?key={api_key}"
ENDPOINT_GROQ = "https://api.groq.com/openai/v1/chat/completions"
ENDPOINT_LOCALAI = "{protocol}://{ip_address}:{port}/v1/chat/completions"
ENDPOINT_OLLAMA = "{protocol}://{ip_address}:{port}/api/generate"
ENDPOINT_OPENWEBUI = "{protocol}://{ip_address}:{port}/api/chat"
ENDPOINT_MISTRAL = "https://api.mistral.ai/v1/chat/completions"
ENDPOINT_PERPLEXITY = "https://api.perplexity.ai/chat/completions"
ENDPOINT_OPENROUTER = "https://openrouter.ai/api/v1/chat/completions"
ENDPOINT_CODESTRAL = "https://codestral.mistral.ai/v1/chat/completions"
ENDPOINT_VENICEAI = "https://api.venice.ai/api/v1/chat/completions"
ENDPOINT_ZHIPUAI = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
ENDPOINT_ANTHROPIC = "https://api.anthropic.com/v1/messages"


# ─────────────────────────────────────────────────────────────
# Sensor Keys
# ─────────────────────────────────────────────────────────────
SENSOR_KEY_SUGGESTIONS = "suggestions"
SENSOR_KEY_STATUS = "status"
SENSOR_KEY_INPUT_TOKENS = "input_tokens"
SENSOR_KEY_OUTPUT_TOKENS = "output_tokens"
SENSOR_KEY_MODEL = "model"
SENSOR_KEY_LAST_ERROR = "last_error"
SENSOR_KEY_TIMEOUT = "timeout"
SENSOR_KEY_TEMPERATURE = "temperature"

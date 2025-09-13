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

# ─────────────────────────────────────────────────────────────
# Provider‑selection key
# ─────────────────────────────────────────────────────────────
CONF_PROVIDER = "provider"

# ─────────────────────────────────────────────────────────────
# Provider‑specific keys
# ─────────────────────────────────────────────────────────────
# OpenAI
CONF_OPENAI_API_KEY = "openai_api_key"
CONF_OPENAI_MODEL = "openai_model"
CONF_OPENAI_TEMPERATURE = "openai_temperature"

# OpenAI Azure
CONF_OPENAI_AZURE_API_KEY = "openai_azure_api_key"
CONF_OPENAI_AZURE_DEPLOYMENT_ID = "openai_azure_deployment_id"
CONF_OPENAI_AZURE_API_VERSION = "openai_azure_api_version"
CONF_OPENAI_AZURE_ENDPOINT = "openai_azure_endpoint"
CONF_OPENAI_AZURE_TEMPERATURE = "openai_azure_temperature"

# Anthropic
CONF_ANTHROPIC_API_KEY = "anthropic_api_key"
CONF_ANTHROPIC_MODEL = "anthropic_model"
CONF_ANTHROPIC_TEMPERATURE = "anthropic_temperature"
VERSION_ANTHROPIC = "2023-06-01"

# Google
CONF_GOOGLE_API_KEY = "google_api_key"
CONF_GOOGLE_MODEL = "google_model"
CONF_GOOGLE_TEMPERATURE = "google_temperature"

# Groq
CONF_GROQ_API_KEY = "groq_api_key"
CONF_GROQ_MODEL = "groq_model"
CONF_GROQ_TEMPERATURE = "groq_temperature"

# LocalAI
CONF_LOCALAI_IP_ADDRESS = "localai_ip"
CONF_LOCALAI_PORT = "localai_port"
CONF_LOCALAI_HTTPS = "localai_https"
CONF_LOCALAI_MODEL = "localai_model"
CONF_LOCALAI_TEMPERATURE = "localai_temperature"

# Ollama
CONF_OLLAMA_IP_ADDRESS = "ollama_ip"
CONF_OLLAMA_PORT = "ollama_port"
CONF_OLLAMA_HTTPS = "ollama_https"
CONF_OLLAMA_MODEL = "ollama_model"
CONF_OLLAMA_TEMPERATURE = "ollama_temperature"
CONF_OLLAMA_DISABLE_THINK = "ollama_disable_think"

# Custom OpenAI
CONF_CUSTOM_OPENAI_ENDPOINT = "custom_openai_endpoint"
CONF_CUSTOM_OPENAI_API_KEY = "custom_openai_api_key"
CONF_CUSTOM_OPENAI_MODEL = "custom_openai_model"
CONF_CUSTOM_OPENAI_TEMPERATURE = "custom_openai_temperature"

# Mistral AI
CONF_MISTRAL_API_KEY = "mistral_api_key"
CONF_MISTRAL_MODEL = "mistral_model"
CONF_MISTRAL_TEMPERATURE = "mistral_temperature"
MISTRAL_MODELS = [
    "mistral-tiny",
    "mistral-small",
    "mistral-medium",
    "mistral-large",
]

# Perplexity AI
CONF_PERPLEXITY_API_KEY = "perplexity_api_key"
CONF_PERPLEXITY_MODEL = "perplexity_model"
CONF_PERPLEXITY_TEMPERATURE = "perplexity_temperature"

# OpenRouter
CONF_OPENROUTER_API_KEY = "openrouter_api_key"
CONF_OPENROUTER_MODEL = "openrouter_model"
CONF_OPENROUTER_REASONING_MAX_TOKENS = "openrouter_reasoning_max_tokens"
CONF_OPENROUTER_TEMPERATURE = "openrouter_temperature"

# Generic OpenAI
CONF_GENERIC_OPENAI_ENDPOINT = "generic_openai_api_endpoint"
CONF_GENERIC_OPENAI_API_KEY = "generic_openai_api_key"
CONF_GENERIC_OPENAI_MODEL = "generic_openai_model"
CONF_GENERIC_OPENAI_TEMPERATURE = "generic_openai_temperature"
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
}

# ─────────────────────────────────────────────────────────────
# Service & attribute names
# ─────────────────────────────────────────────────────────────
ATTR_PROVIDER_CONFIG = "provider_config"
ATTR_CUSTOM_PROMPT = "custom_prompt"
SERVICE_GENERATE_SUGGESTIONS = "generate_suggestions"

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
ENDPOINT_OLLAMA = "{protocol}://{ip_address}:{port}/api/chat"
ENDPOINT_MISTRAL = "https://api.mistral.ai/v1/chat/completions"
ENDPOINT_PERPLEXITY = "https://api.perplexity.ai/chat/completions"
ENDPOINT_OPENROUTER = "https://openrouter.ai/api/v1/chat/completions"


# ─────────────────────────────────────────────────────────────
# Sensor Keys
# ─────────────────────────────────────────────────────────────
SENSOR_KEY_SUGGESTIONS = "suggestions"
SENSOR_KEY_STATUS = "status"
SENSOR_KEY_INPUT_TOKENS = "input_tokens"
SENSOR_KEY_OUTPUT_TOKENS = "output_tokens"
SENSOR_KEY_MODEL = "model"
SENSOR_KEY_LAST_ERROR = "last_error"

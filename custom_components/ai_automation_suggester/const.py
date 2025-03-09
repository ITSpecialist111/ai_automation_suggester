# custom_components/ai_automation_suggester/const.py

"""Constants for the AI Automation Suggester integration."""

DOMAIN = "ai_automation_suggester"
PLATFORMS = ["sensor"]

# Config version
CONFIG_VERSION = 2

# Provider configuration
CONF_PROVIDER = "provider"

# OpenAI specific
CONF_OPENAI_API_KEY = "openai_api_key"
CONF_OPENAI_MODEL = "openai_model"

# Anthropic specific
CONF_ANTHROPIC_API_KEY = "anthropic_api_key"
CONF_ANTHROPIC_MODEL = "anthropic_model"
VERSION_ANTHROPIC = "2023-06-01"

# Google specific
CONF_GOOGLE_API_KEY = "google_api_key"
CONF_GOOGLE_MODEL = "google_model"

# Groq specific
CONF_GROQ_API_KEY = "groq_api_key"
CONF_GROQ_MODEL = "groq_model"

# LocalAI specific
CONF_LOCALAI_IP_ADDRESS = "localai_ip"
CONF_LOCALAI_PORT = "localai_port"
CONF_LOCALAI_HTTPS = "localai_https"
CONF_LOCALAI_MODEL = "localai_model"

# Ollama specific
CONF_OLLAMA_IP_ADDRESS = "ollama_ip"
CONF_OLLAMA_PORT = "ollama_port"
CONF_OLLAMA_HTTPS = "ollama_https"
CONF_OLLAMA_MODEL = "ollama_model"

# Custom OpenAI specific
CONF_CUSTOM_OPENAI_ENDPOINT = "custom_openai_endpoint"
CONF_CUSTOM_OPENAI_API_KEY = "custom_openai_api_key"
CONF_CUSTOM_OPENAI_MODEL = "custom_openai_model"

# Mistral AI specific (new)
CONF_MISTRAL_API_KEY = "mistral_api_key"
CONF_MISTRAL_MODEL = "mistral_model"
MISTRAL_MODELS = ["mistral-tiny", "mistral-small", "mistral-medium", "mistral-large"]

# Model Defaults
DEFAULT_MODELS = {
    "OpenAI": "gpt-4o-mini",
    "Anthropic": "claude-2.1",
    "Google": "gemini-1.0-pro",
    "Groq": "llama3-8b-8192",
    "LocalAI": "llama3",
    "Ollama": "llama2",
    "Custom OpenAI": "gpt-3.5-turbo",
    "Mistral AI": "mistral-medium"
}

# Error Messages
ERROR_INVALID_API_KEY = "Invalid API key"
ERROR_CONNECTION_FAILED = "Could not connect to server"
ERROR_INVALID_CONFIG = "Invalid configuration"
ERROR_OPENAI_NOT_CONFIGURED = "OpenAI is not configured"
ERROR_ANTHROPIC_NOT_CONFIGURED = "Anthropic is not configured"
ERROR_GOOGLE_NOT_CONFIGURED = "Google is not configured"
ERROR_GROQ_NOT_CONFIGURED = "Groq is not configured"
ERROR_GROQ_MULTIPLE_IMAGES = "Groq does not support videos or streams"
ERROR_LOCALAI_NOT_CONFIGURED = "LocalAI is not configured"
ERROR_OLLAMA_NOT_CONFIGURED = "Ollama is not configured"
ERROR_CUSTOM_OPENAI_NOT_CONFIGURED = "Custom OpenAI provider is not configured"
ERROR_NO_IMAGE_INPUT = "No image input provided"
ERROR_HANDSHAKE_FAILED = "Connection could not be established"

# Service attributes
ATTR_PROVIDER_CONFIG = "provider_config"
ATTR_CUSTOM_PROMPT = "custom_prompt"

SERVICE_GENERATE_SUGGESTIONS = "generate_suggestions"

# Provider statuses
PROVIDER_STATUS_CONNECTED = "connected"
PROVIDER_STATUS_DISCONNECTED = "disconnected"
PROVIDER_STATUS_ERROR = "error"

# Event types
EVENT_NEW_SUGGESTION = f"{DOMAIN}_new_suggestion"
EVENT_PROVIDER_STATUS_CHANGE = f"{DOMAIN}_provider_status_change"

# Configuration defaults
CONF_MAX_TOKENS = "max_tokens"
DEFAULT_MAX_TOKENS = 500  # Conservative default; adjust as needed per provider
DEFAULT_TEMPERATURE = 0.7

# API Endpoints
ENDPOINT_OPENAI = "https://api.openai.com/v1/chat/completions"
ENDPOINT_ANTHROPIC = "https://api.anthropic.com/v1/messages" 
ENDPOINT_GOOGLE = "https://generativelanguage.googleapis.com/v1beta2/models/{model}:generateText?key={api_key}"
ENDPOINT_GROQ = "https://api.groq.com/openai/v1/chat/completions"
ENDPOINT_LOCALAI = "{protocol}://{ip_address}:{port}/v1/chat/completions"
ENDPOINT_OLLAMA = "{protocol}://{ip_address}:{port}/api/chat"
ENDPOINT_MISTRAL = "https://api.mistral.ai/v1/chat/completions"
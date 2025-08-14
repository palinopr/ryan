"""
Configuration settings for Campaign Report Agent
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class OpenAISettings(BaseSettings):
    """OpenAI configuration"""
    api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    model: str = Field(default="gpt-4o", alias="OPENAI_MODEL")  # Using GPT-4o 
    temperature: float = Field(default=0.3, alias="OPENAI_TEMPERATURE")
    
    class Config:
        env_file = ".env"
        populate_by_name = True
        extra = "ignore"


class AnthropicSettings(BaseSettings):
    """Anthropic configuration"""
    api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    model: str = Field(default="claude-3-5-sonnet-20241022", env="ANTHROPIC_MODEL")
    temperature: float = Field(default=0.3, env="ANTHROPIC_TEMPERATURE")


class MetaAdsSettings(BaseSettings):
    """Meta/Facebook Ads API configuration"""
    access_token: Optional[str] = Field(default=None, alias="META_ACCESS_TOKEN")
    app_id: Optional[str] = Field(default=None, alias="META_APP_ID")
    app_secret: Optional[str] = Field(default=None, alias="META_APP_SECRET")
    ad_account_id: Optional[str] = Field(default=None, alias="META_AD_ACCOUNT_ID")
    api_version: str = Field(default="v21.0", alias="META_API_VERSION")
    base_url: str = Field(default="https://graph.facebook.com", alias="META_BASE_URL")
    
    # Rate limiting
    rate_limit_requests: int = Field(default=200, alias="META_RATE_LIMIT_REQUESTS")
    rate_limit_period: int = Field(default=3600, alias="META_RATE_LIMIT_PERIOD")
    max_retries: int = Field(default=3, alias="META_MAX_RETRIES")
    retry_delay: int = Field(default=1, alias="META_RETRY_DELAY")
    timeout: int = Field(default=30, alias="META_TIMEOUT")
    
    class Config:
        env_file = ".env"
        populate_by_name = True
        extra = "ignore"


class CampaignSettings(BaseSettings):
    """Campaign analysis configuration"""
    hot_lead_threshold: int = Field(default=8, env="HOT_LEAD_THRESHOLD")
    warm_lead_threshold: int = Field(default=6, env="WARM_LEAD_THRESHOLD")
    max_contacts_per_analysis: int = Field(default=100, env="MAX_CONTACTS_PER_ANALYSIS")
    max_opportunities_per_analysis: int = Field(default=50, env="MAX_OPPORTUNITIES_PER_ANALYSIS")
    max_conversations_per_analysis: int = Field(default=30, env="MAX_CONVERSATIONS_PER_ANALYSIS")


class LangSmithSettings(BaseSettings):
    """LangSmith configuration"""
    tracing_v2: bool = Field(default=True, env="LANGCHAIN_TRACING_V2")
    api_key: Optional[str] = Field(default=None, env="LANGCHAIN_API_KEY")
    project: str = Field(default="campaign-report-agent", env="LANGCHAIN_PROJECT")
    endpoint: str = Field(default="https://api.smith.langchain.com", env="LANGCHAIN_ENDPOINT")


class Settings(BaseSettings):
    """Main settings"""
    app_name: str = Field(default="Campaign Report Agent", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="APP_DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    environment: str = Field(default="production", env="ENVIRONMENT")
    
    # Sub-configurations
    openai: OpenAISettings = Field(default_factory=OpenAISettings)
    anthropic: AnthropicSettings = Field(default_factory=AnthropicSettings)
    meta_ads: MetaAdsSettings = Field(default_factory=MetaAdsSettings)
    campaign: CampaignSettings = Field(default_factory=CampaignSettings)
    langsmith: LangSmithSettings = Field(default_factory=LangSmithSettings)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get singleton settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
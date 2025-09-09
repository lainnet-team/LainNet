from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    base_domain: str
    app_id: str
    app_secret: str
    tmp_dir: str = "./tmp"

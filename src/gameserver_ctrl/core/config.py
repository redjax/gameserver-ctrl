from typing import Union
from pathlib import Path

from dynaconf import settings
from pydantic import BaseModel, Field, validator, ValidationError
from loguru import logger as log


class AppSettings(BaseModel):
    env: str = Field(default=settings.ENV, env="ENV")
    container_env: bool = Field(default=settings.CONTAINER_ENV, env="CONTAINER_ENV")
    log_level: str = Field(default=settings.LOG_LEVEL, env="LOG_LEVEL")

    data_dir: Union[str, Path] = Field(default=Path(".data"), env="DATA_DIR")
    template_dir: Union[str, Path] = Field(
        default=Path("templates"), env="TEMPLATES_DIR"
    )

    @validator("template_dir", "data_dir")
    def valid_template_dir(cls, v) -> Path:
        if isinstance(v, str):
            return Path(v)

        return v


app_settings: AppSettings = AppSettings()

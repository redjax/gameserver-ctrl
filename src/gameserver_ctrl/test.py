from __future__ import annotations

import sys

sys.path.append(".")

from typing import Union
from uuid import UUID, uuid4

from gameserver_ctrl.constants import DATA_DIR, OUTPUT_DIR, TEMPLATES_DIR
from gameserver_ctrl.core.config import app_settings
from gameserver_ctrl.domain.minecraft import (
    ForgeServerComposeFile,
    ForgeServerEnvData,
    ForgeServerEnvFile,
    MCForgeServer,
    WhitelistFile,
    WhitelistPlayer,
)

from dynaconf import settings
from loguru import logger as log
from red_utils.ext.loguru_utils import LoguruSinkStdOut, init_logger

def create_test_whitelist(create_player_count: int = 3) -> WhitelistFile:
    test_player_dicts: list[dict] = []
    test_players: list[WhitelistPlayer] = []

    while create_player_count > 0:
        player_dict: dict = {"id": str(uuid4()), "name": f"test{create_player_count}"}
        test_player_dicts.append(player_dict)

        player: WhitelistPlayer = WhitelistPlayer.model_validate(player_dict)
        test_players.append(player)

        create_player_count -= 1

    log.debug(f"Created [{len(test_players)}] test players.")
    if len(test_players) > 0:
        for p in test_players:
            log.debug(f"\tPlayer: {p}")

    whitelist: WhitelistFile = WhitelistFile(players=test_players)

    return whitelist


def create_env_file(env_data: ForgeServerEnvData = None) -> ForgeServerEnvFile:
    env_file: ForgeServerEnvFile = ForgeServerEnvFile.model_validate(
        {"output_path": "test", "env_data": env_data}
    )
    log.debug(f"ENV file: {env_file}")

    return env_file


if __name__ == "__main__":
    init_logger(sinks=[LoguruSinkStdOut(level=settings.LOG_LEVEL).as_dict()])

    log.info(
        f"[env:{settings.ENV}|container:{settings.CONTAINER_ENV}] App Start -- Game: {settings.GAME}"
    )

    log.debug(f"App settings: {app_settings}")

    whitelist = create_test_whitelist()
    log.debug(f"Whitelist: {whitelist}")

    test_env_data: ForgeServerEnvData = ForgeServerEnvData.model_validate(
        {
            "image_tag": "testing",
            "container_name": "test_container",
            "server_port": 25565,
            "server_type": "test",
            "server_ver": "2.15",
            "server_debug": True,
            "whitelist_enable": True,
            "mods_dir": "test/mods",
            "whitelist_file": "test/whitelist.json",
            "whitelist_override": False,
        }
    )
    # log.debug(f"ENV data: {test_env_data}")

    env_file: ForgeServerEnvFile = create_env_file(test_env_data)
    log.debug(f"ENV file: {env_file}")

    compose_file: ForgeServerComposeFile = ForgeServerComposeFile()
    log.debug(f"Compose file: {compose_file}")

    mc_server: MCForgeServer = MCForgeServer(
        env_file=env_file, whitelist_file=whitelist, compose_file=compose_file
    )
    log.debug(f"Minecraft Server: {mc_server}")

    mc_server.create_server()

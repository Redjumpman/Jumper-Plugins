from typing import Dict, Optional

import discord
from redbot.core import Config


class OldMessageTypeManager:
    def __init__(self, config: Config, enable_cache: bool = True):
        self._config: Config = config
        self.enable_cache = enable_cache
        self._cached_guild: Dict[int, bool] = {}

    async def get_guild(self, guild: discord.Guild) -> bool:
        ret: bool
        gid: int = guild.id
        if self.enable_cache and gid in self._cached_guild:
            ret = self._cached_guild[gid]
        else:
            ret = await self._config.guild_from_id(gid).use_old_style()
            self._cached_guild[gid] = ret
        return ret

    async def set_guild(self, guild: discord.Guild, set_to: Optional[bool]) -> None:
        gid: int = guild.id
        if set_to is not None:
            await self._config.guild_from_id(gid).use_old_style.set(set_to)
            self._cached_guild[gid] = set_to
        else:
            await self._config.guild_from_id(gid).use_old_style.clear()
            self._cached_guild[gid] = self._config.defaults["GUILD"]["use_old_style"]

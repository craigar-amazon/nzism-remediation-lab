from lib.base import ConfigError

import cfg.core, cfg.roles

def get_list_len(src: list, srcPath) -> list:
    if src is None: raise ConfigError("{} is undefined".format(srcPath))
    return len(src)

def getList(src: list, srcPath) -> list:
    if src is None: raise ConfigError("{} is undefined".format(srcPath))
    if len(src) == 0: raise ConfigError("{} is empty".format(srcPath))
    return src

def getMap(src: dict, srcPath) -> dict:
    if src is None: raise ConfigError("{} is undefined".format(srcPath))
    if len(src) == 0: raise ConfigError("{} is empty".format(srcPath))
    return src

def getMapValue(map, mapPath, key):
    value = getMap(map, mapPath).get(key, None)
    if value is None: raise ConfigError("{} in {} is undefined", key, mapPath)
    return value

def getCoreEventBusCfgValue(key):
    return getMapValue(cfg.core.coreEventBusCfg(), "cfg.core.coreEventBusCfg", key)

def getCoreQueueCfgValue(key):
    return getMapValue(cfg.core.coreQueueCfg(), "cfg.core.coreQueueCfg", key)

def getStandaloneRolesCfgValue(key):
    return getMapValue(cfg.roles.standaloneRoles(), "cfg.roles.standaloneRoles", key)

def isLandingZoneSearchDisabled():
    return get_list_len(cfg.roles.landingZoneSearch(), "cfg.roles.landingZoneSearch") == 0

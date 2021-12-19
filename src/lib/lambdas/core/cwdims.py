import logging
from typing import List

import cfg.core as cfgCore
from lib.base.request import DispatchEvent

class _Generator:
    def __init__(self, key: str, value):
        self.key = key
        self.valueList = value if type(value) is list else [value]

    def __str__(self): return "{}=[{}]".format(self.key, ",".join(self.valueList))

class _Product:
    def __init__(self):
        self._map = {}

    def put(self, key: str, value: str):
        self._map[key] = value
        return self

    def update(self, srcMap :dict):
        self._map.update(srcMap)
        return self

    def newProduct(self, key: str, value: str):
        return _Product().update(self._map).put(key, value)

    def toDict(self):
        return dict(self._map)

class _Cross:
    def __init__(self):
        self._productList = []

    def initialise(self, generator: _Generator):
        productList = [] 
        key = generator.key
        for val in generator.valueList:
            product = _Product().put(key, val)
            productList.append(product)
        self._productList = productList
        return self

    def multipliedBy(self, generator: _Generator):
        newCross = _Cross()
        key = generator.key
        for product in self._productList:
            for val in generator.valueList:
                newProduct = product.newProduct(key, val)
                newCross._productList.append(newProduct)
        return newCross

    def productList(self):
        return self._productList

def _create_default_generator(dimName : str) -> _Generator:
    return _Generator(dimName, ['Unspecified'])

def _create_generator_from_tag(dimName, event :DispatchEvent):
    tagStart = dimName.index('.') + 1
    tagName = dimName[tagStart:]
    if len(tagName) == 0:
        logging.warning("Malformed CloudWatch dimension name `%s`", dimName)
        return _create_default_generator('AutoResourceTag')
    tagValue = event.autoResourceTags.get(tagName)
    if not tagValue:
        logging.info("CloudWatch dimension tag `%s` is undefined", tagName)
        return _create_default_generator(tagName)
    valueList = str(tagValue).split('+')
    return _Generator(tagName, valueList)

def _create_generator(dimName :str, event :DispatchEvent) -> _Generator:
    cdimName = dimName.lower()
    if cdimName == 'configrule': return _Generator('ConfigRule', event.configRuleName)
    if cdimName == 'account': return _Generator('Account', [event.target.accountName])
    if cdimName == 'region': return _Generator('Region', [event.target.regionName])
    if cdimName == 'resourcetype': return _Generator('ResourceType', [event.target.resourceType])
    if cdimName.startswith('autoresourcetag.'): return _create_generator_from_tag(dimName, event)
    logging.warning("CloudWatch dimension `%s` is not supported", dimName)
    return _create_default_generator(dimName)

def _path_to_crossproduct(event :DispatchEvent, dimPath :str) -> _Cross:
    dimNames = dimPath.split('/')
    exCross = None
    for dimName in dimNames:
        generator = _create_generator(dimName, event)
        if exCross:
            newCross = exCross.multipliedBy(generator)
        else:
            newCross = _Cross().initialise(generator)
        exCross = newCross
    return exCross

def get_product_list(event :DispatchEvent, dimList) -> List[_Product]:
    productList = []
    for dimPath in dimList:
        optCross = _path_to_crossproduct(event, dimPath)
        if not optCross: continue
        productList.extend(optCross.productList())
    return productList

def get_dimension_maps(event :DispatchEvent, dimList):
    cdimList = [dimList] if type(dimList) is str else list(dimList)
    dmMapList = []
    productList = get_product_list(event, cdimList)
    for product in productList:
        dmMapList.append(product.toDict())
    return dmMapList

def getDimensionMaps(event :DispatchEvent):
    action = event.action
    dimList = cfgCore.coreCloudWatchDimensionList(action)
    return get_dimension_maps(event, dimList)



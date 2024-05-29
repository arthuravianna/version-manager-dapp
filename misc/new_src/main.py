import logging

from cartesi import Rollup, RollupData

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def str2hex(str):
    """Encodes a string as a hex string"""
    return "0x" + str.encode("utf-8").hex()



def setup(HLFdapp, HLFjson_router, HLFurl_router, URLParameters):
    
    @HLFurl_router.advance('hello/')
    def hello_world_advance(rollup: Rollup, data: RollupData) -> bool:
        rollup.notice(str2hex('Hello World'))
        return True


    @HLFurl_router.inspect('hello/')
    def hello_world_inspect(rollup: Rollup, data: RollupData) -> bool:
        rollup.report(str2hex('Hello World'))
        return True


    @HLFurl_router.inspect('hello/{name}')
    def hello_world_inspect_parms(rollup: Rollup, params: URLParameters) -> bool:
        msg = f'Hello {params.path_params["name"]}'
        if 'suffix' in params.query_params:
            msg += params.query_params["suffix"][0]

        rollup.report(str2hex(msg))
        return True
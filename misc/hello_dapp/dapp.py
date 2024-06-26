import logging

from cartesi import DApp, Rollup, RollupData, URLRouter, URLParameters

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)
dapp = DApp()
url_router = URLRouter()
dapp.add_router(url_router)


def str2hex(str):
    """Encodes a string as a hex string"""
    return "0x" + str.encode("utf-8").hex()


@url_router.advance('hello/')
def hello_world_advance(rollup: Rollup, data: RollupData) -> bool:
    rollup.notice(str2hex('Hello World'))
    return True


@url_router.inspect('hello/')
def hello_world_inspect(rollup: Rollup, data: RollupData) -> bool:
    rollup.report(str2hex('Hello World'))
    return True


@url_router.inspect('hello/{name}')
def hello_world_inspect_parms(rollup: Rollup, params: URLParameters) -> bool:
    msg = f'Hello {params.path_params["name"]}'
    if 'suffix' in params.query_params:
        msg += params.query_params["suffix"][0]

    rollup.report(str2hex(msg))
    return True


if __name__ == '__main__':
    dapp.run()
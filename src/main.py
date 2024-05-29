import logging

from cartesi import Rollup, RollupData

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def str2hex(str):
    """Encodes a string as a hex string"""
    return "0x" + str.encode("utf-8").hex()



def setup(HLFdapp, HLFurl_router, HLFjson_router, URLParameters):
    @HLFdapp.advance()
    def handle_advance(rollup: Rollup, data: RollupData) -> bool:
        payload = data.str_payload()
        LOGGER.debug("Echoing '%s'", payload)
        rollup.notice(str2hex(payload))
        return True


    @HLFdapp.inspect()
    def handle_inspect(rollup: Rollup, data: RollupData) -> bool:
        payload = data.str_payload()
        LOGGER.debug("Echoing '%s'", payload)
        rollup.report(str2hex(payload))
        return True
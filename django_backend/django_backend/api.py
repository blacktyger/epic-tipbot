from pprint import pprint
import json

from ninja_extra import NinjaExtraAPI
from ipware import get_client_ip


api = NinjaExtraAPI()


@api.post('/')
def receive(request):
    payload = json.loads(request.body.decode('utf-8'))
    pprint(request.__dict__)

    if payload['method'] == 'check_version':
        pprint(payload)
        return {
            "id": 1,
            "jsonrpc": "2.0",
            "result": {
                "Ok": {
                    "foreign_api_version": 2,
                    "supported_slate_versions": [
                        "V3",
                        "V2"
                        ]
                    }
                }
            }
    elif payload['method'] == 'receive_tx':
        wallet_id = request.path.split('/')[2]
        return {'lol': 'lol'}

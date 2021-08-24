import os
import json

import funcx_endpoint


def register_endpoint(logger, funcx_client, endpoint_uuid, endpoint_dir, name):
    """Register the endpoint and return the registration info.

    Parameters
    ----------
    funcx_client : FuncXClient
        The auth'd client to communicate with the funcX service

    endpoint_uuid : str
        The uuid to register the endpoint with

    endpoint_dir : str
        The endpoint directory path to store data in

    name : str
        The name of the endpoint
    """
    logger.debug("Attempting registration")
    logger.debug(f"Trying with eid : {endpoint_uuid}")
    reg_info = funcx_client.register_endpoint(name,
                                              endpoint_uuid,
                                              endpoint_version=funcx_endpoint.__version__)

    # this is a backup error handler in case an endpoint ID is not sent back
    # from the service or a bad ID is sent back
    if 'endpoint_id' not in reg_info:
        raise Exception("Endpoint ID was not included in the service's registration response.")
    elif not isinstance(reg_info['endpoint_id'], str):
        raise Exception("Endpoint ID sent by the service was not a string.")

    with open(os.path.join(endpoint_dir, 'endpoint.json'), 'w+') as fp:
        json.dump(reg_info, fp)
        logger.debug("Registration info written to {}".format(os.path.join(endpoint_dir, 'endpoint.json')))

    certs_dir = os.path.join(endpoint_dir, 'certificates')
    os.makedirs(certs_dir, exist_ok=True)
    server_keyfile = os.path.join(certs_dir, 'server.key')
    logger.debug(f"Writing server key to {server_keyfile}")
    try:
        with open(server_keyfile, 'w') as f:
            f.write(reg_info['forwarder_pubkey'])
            os.chmod(server_keyfile, 0o600)
    except Exception:
        logger.exception("Failed to write server certificate")

    return reg_info

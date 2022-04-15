import json
import os

import pika

import funcx
import funcx_endpoint
from funcx_endpoint.endpoint.register_endpoint import (
    mock_register_endpoint,
    register_endpoint,
)

ENDPOINT_UUID = "c65f076d-d731-406a-bb55-137faef153b8"


def test_mock_register_ep():
    res = mock_register_endpoint(
        endpoint_name="foo",
        endpoint_uuid=ENDPOINT_UUID,
        endpoint_version=funcx_endpoint.__version__,
    )

    assert isinstance(res, str)
    conn_params = pika.URLParameters(res)
    assert conn_params


def test_register_ep():
    endpoint_name = "endpoint_foo"
    fxc = funcx.FuncXClient()
    json_dir = os.getcwd()
    reg_info = register_endpoint(
        fxc,
        endpoint_uuid=ENDPOINT_UUID,
        endpoint_dir=json_dir,
        endpoint_name=endpoint_name,
    )
    assert isinstance(reg_info, pika.URLParameters)

    assert os.path.exists(f"{json_dir}/endpoint.json")

    with open(f"{json_dir}/endpoint.json") as f:
        data = json.load(f)
        assert data["endpoint_id"] == ENDPOINT_UUID
        assert data["endpoint_name"] == endpoint_name
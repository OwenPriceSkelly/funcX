import typing as t

import pytest
from globus_compute_endpoint.endpoint.config import Config
from globus_compute_endpoint.endpoint.config.model import ConfigModel
from pydantic.error_wrappers import ValidationError


@pytest.fixture
def config_dict():
    return {"engine": {"type": "GlobusComputeEngine"}}


@pytest.fixture
def config_dict_mu(tmp_path):
    idc = tmp_path / "idconf.json"
    idc.write_text("[]")
    return {
        "identity_mapping_config_path": idc,
        "multi_user": True,
    }


@pytest.mark.parametrize(
    "data",
    [
        ("worker_ports", (50000, 55000)),
        ("worker_port_range", (50000, 55000)),
        ("interchange_port_range", (50000, 55000)),
    ],
)
def test_config_model_tuple_conversions(config_dict: dict, data: t.Tuple[str, t.Tuple]):
    field, expected_val = data

    config_dict["engine"][field] = expected_val
    model = ConfigModel(**config_dict)
    assert getattr(model.engine.executor, field) == expected_val

    config_dict["engine"][field] = list(expected_val)
    model = ConfigModel(**config_dict)
    assert getattr(model.engine.executor, field) == expected_val

    config_dict["engine"][field] = 50000
    with pytest.raises(ValueError):
        ConfigModel(**config_dict)


def test_config_enforces_engine(config_dict):
    del config_dict["engine"]
    with pytest.raises(ValidationError) as pyt_exc:
        ConfigModel(**config_dict)

    assert "missing engine" in str(pyt_exc.value)


def test_config_enforces_no_identity_mapping_conf(config_dict, tmp_path):
    conf_p = tmp_path / "some file"
    conf_p.write_text("[]")
    config_dict["identity_mapping_config_path"] = conf_p
    with pytest.raises(ValidationError) as pyt_exc:
        ConfigModel(**config_dict)

    assert "identity_mapping_config_path should not be specified" in str(pyt_exc.value)


def test_mu_config_enforces_no_engine(config_dict_mu):
    config_dict_mu["engine"] = {"type": "ThreadPoolEngine"}
    with pytest.raises(ValidationError) as pyt_exc:
        ConfigModel(**config_dict_mu)

    assert "no engine if multi-user" in str(pyt_exc), pyt_exc


def test_mu_config_requires_identity_mapping_exists(config_dict_mu, tmp_path):
    config_dict_mu["identity_mapping_config_path"] = tmp_path / "not exists file"
    with pytest.raises(ValidationError) as pyt_exc:
        ConfigModel(**config_dict_mu)

    assert "not exists file" in str(pyt_exc.value)
    assert "does not exist" in str(pyt_exc.value)


def test_config_warns_bad_identity_mapping_path(mocker, config_dict_mu, tmp_path):
    conf_p = tmp_path / "not exists file"
    config_dict_mu["identity_mapping_config_path"] = conf_p
    mock_warn = mocker.patch("globus_compute_endpoint.endpoint.config.config.warnings")
    Config(**config_dict_mu)

    warn_a = mock_warn.warn.call_args[0][0]
    assert mock_warn.warn.called
    assert "Identity mapping config" in warn_a
    assert "path not found" in warn_a
    assert str(conf_p) in warn_a, "expect include location of file in warning"

"""Regression checks for persistent Yak setup: rollback, upgrades and validation."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
import pytest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('yak_setup',ROOT/'tools/yak/configure.py')
setup=importlib.util.module_from_spec(spec);spec.loader.exec_module(setup)

@pytest.fixture(autouse=True)
def windows_contract(monkeypatch):
    # Existing rollback/reuse tests exercise the released Windows contract on any host.
    monkeypatch.setattr(setup, 'host_details', lambda: dict(system='windows', architecture='amd64', python_relative='venv/Scripts/python.exe', setup='SETUP-PYTHON.cmd'))


def package(tmp_path):
    pkg=tmp_path/'package';source=pkg/'source'
    for name in ['tool/worker.py','requirements-runtime-lock.txt','tool/requirements-tested.txt','vendor/upstream-sha256.json']:
        p=source/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('# fixture')
    return pkg

def ready(pkg,state):
    identity=setup.runtime_id(pkg/'source');runtime=state/'runtimes'/identity
    worker=runtime/'source/tool/worker.py';worker.parent.mkdir(parents=True);worker.write_text('# worker')
    (runtime/'ready.json').write_text(json.dumps({'schema':1,'runtime_id':identity}))
    cfg={'schema':'topoptlab-runtime-v1','runtime_id':identity,'python':str(runtime/'venv/Scripts/python.exe'),'worker':str(worker)}
    setup.atomic_json(state/'settings.json',cfg)
    return cfg

def test_runtime_identity_ignores_package_version_path_and_docs(tmp_path):
    a=package(tmp_path/'a');b=package(tmp_path/'b')
    assert setup.runtime_id(a/'source')==setup.runtime_id(b/'source')
    (b/'source/README.md').write_text('new manual')
    assert setup.runtime_id(a/'source')==setup.runtime_id(b/'source')
    (b/'source/tool/worker.py').write_text('# changed worker')
    assert setup.runtime_id(a/'source')!=setup.runtime_id(b/'source')

def test_failed_setup_preserves_active_config_and_releases_lock(tmp_path):
    pkg=package(tmp_path);state=tmp_path/'state';state.mkdir()
    old={'worker':'existing-working-worker','python':'existing-python'}
    setup.atomic_json(state/'settings.json',old)
    with patch.object(setup,'PACKAGE',pkg),patch.object(sys,'argv',['setup','--state-dir',str(state)]),patch.object(setup.venv,'EnvBuilder'),patch.object(setup.subprocess,'run',side_effect=subprocess.CalledProcessError(1,['pip'])):
        with pytest.raises(subprocess.CalledProcessError):setup.main()
    assert json.loads((state/'settings.json').read_text())==old
    assert not (state/'setup.lock').exists()
    assert not list(state.rglob('ready.json'))

def test_upgrade_reuses_ready_runtime_without_installing_packages(tmp_path):
    pkg=package(tmp_path);state=tmp_path/'state';cfg=ready(pkg,state)
    with patch.object(setup,'PACKAGE',pkg),patch.object(sys,'argv',['setup','--state-dir',str(state)]),patch.object(setup.venv,'EnvBuilder') as builder,patch.object(setup.subprocess,'run') as run:
        setup.main()
    builder.assert_not_called()
    assert run.call_count==1 and run.call_args.args[0][1]=='-c'
    assert json.loads((state/'settings.json').read_text())==cfg

def test_check_only_rejects_missing_active_settings(tmp_path):
    pkg=package(tmp_path);state=tmp_path/'state';ready(pkg,state)
    (state/'settings.json').unlink()
    with patch.object(setup,'PACKAGE',pkg),patch.object(sys,'argv',['setup','--check-only','--state-dir',str(state)]),patch.object(setup.subprocess,'run'):
        with pytest.raises(SystemExit,match='active settings'):setup.main()
    assert not (state/'setup.lock').exists()

def test_concurrent_setup_does_not_remove_existing_lock(tmp_path):
    pkg=package(tmp_path);state=tmp_path/'state';state.mkdir();(state/'setup.lock').touch()
    with patch.object(setup,'PACKAGE',pkg),patch.object(sys,'argv',['setup','--state-dir',str(state)]):
        with pytest.raises(SystemExit,match='Another setup'):setup.main()
    assert (state/'setup.lock').is_file()


@pytest.mark.parametrize('arch', ['arm64', 'x86_64'])
def test_mac_setup_has_native_venv_architecture_and_binary_wheel_policy(tmp_path, arch):
    pkg=package(tmp_path);state=tmp_path/'state'
    host=dict(system='macos',architecture=arch,python_relative='venv/bin/python',setup='SETUP-PYTHON.command')
    with patch.object(setup,'PACKAGE',pkg),patch.object(setup,'host_details',return_value=host),patch.object(sys,'argv',['setup','--state-dir',str(state)]),patch.object(setup.venv,'EnvBuilder'),patch.object(setup.subprocess,'run') as run:
        setup.main()
    cfg=json.loads((state/'settings.json').read_text())
    assert cfg['architecture']==arch and cfg['platform']=='macos'
    assert Path(cfg['python']).parts[-2:]==('bin','python')
    assert '-macos-'+arch in cfg['python']
    assert any('--only-binary='+setup.NATIVE_WHEELS in c.args[0] for c in run.call_args_list)
    with patch.object(setup,'PACKAGE',pkg),patch.object(setup,'host_details',return_value=host),patch.object(sys,'argv',['setup','--check-only','--state-dir',str(state)]),patch.object(setup.venv,'EnvBuilder') as builder,patch.object(setup.subprocess,'run') as run:
        setup.main()
    builder.assert_not_called();assert run.call_count==1


def test_mac_state_directory_is_application_support(tmp_path):
    with patch.object(setup.Path,'home',return_value=tmp_path):
        assert setup.default_state({'system':'macos'})==tmp_path/'Library/Application Support/TopOptLab/Rhino8'


def test_mac_native_checks_reject_old_os_and_rosetta_before_setup():
    # Call the real host check, rather than the fixture that simulates Windows.
    import importlib.util
    spec=importlib.util.spec_from_file_location('mac_host_check',ROOT/'tools/yak/configure.py')
    native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
    with patch.object(native.sys,'platform','darwin'),patch.object(native.platform,'mac_ver',return_value=('14.7',(),'')):
        with pytest.raises(ValueError,match='macOS 15'):native.host_details()
    translated=subprocess.CompletedProcess([],0,stdout='1\n')
    with patch.object(native.sys,'platform','darwin'),patch.object(native.platform,'mac_ver',return_value=('15.0',(),'')),patch.object(native.platform,'machine',return_value='x86_64'),patch.object(native.subprocess,'run',return_value=translated):
        with pytest.raises(ValueError,match='Rosetta'):native.host_details()

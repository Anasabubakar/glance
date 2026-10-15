import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "glance", "shell"))

import frozen_env  # noqa: E402


def test_clean_env_restores_original_library_path():
    out = frozen_env.clean_env({"LD_LIBRARY_PATH": "/opt/glance/_internal",
                                "LD_LIBRARY_PATH_ORIG": "/usr/lib/x", "A": "1"})
    assert out["LD_LIBRARY_PATH"] == "/usr/lib/x" and out["A"] == "1"
    assert "LD_LIBRARY_PATH_ORIG" not in out


def test_clean_env_drops_bundle_path_when_no_original():
    assert "LD_LIBRARY_PATH" not in frozen_env.clean_env({"LD_LIBRARY_PATH": "/opt/glance/_internal"})

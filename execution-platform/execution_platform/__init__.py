
# Extend package path to include src/execution_platform for providers and shared code
import pathlib
_pkg_dir = pathlib.Path(__file__).resolve().parent
_src_pkg = _pkg_dir.parent / "src" / "execution_platform"
if _src_pkg.exists():
    try:
        __path__  # type: ignore[name-defined]
        __path__ = list(set(list(__path__) + [str(_src_pkg)]))  # type: ignore[assignment]
    except NameError:
        __path__ = [str(_src_pkg)]  # type: ignore[assignment]

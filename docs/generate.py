import json
from pathlib import Path
from typing import Iterable
import argparse

import yaml
from pydantic.main import ModelMetaclass

DOCS_DIR = Path(__file__).resolve().parent


def _get_pydantic_classes(package_name: str) -> Iterable[ModelMetaclass]:
    """
    Args:
        package_name:

    Returns:
        List `pydantic` models specified in __all__ of giving package.
    Raises:
        ValueError: In case if __all__ for giving package is not defined.
    """
    # See Note in <https://docs.python.org/3/library/functions.html#exec>
    explicit_locals = {}
    try:
        exec(
            f"from {package_name} import __all__ as public_class_names",
            globals(),
            explicit_locals,
        )
        public_class_names = explicit_locals["public_class_names"]
    except ImportError:
        raise ValueError(f"Please define `__all__` in package `{package_name}`")

    public_classes = []
    for cls_name in public_class_names:
        exec(f"from {package_name} import {cls_name} as cls", globals(), explicit_locals)
        public_classes.append(explicit_locals["cls"])
    pydantic_classes = (
        cls for cls in public_classes if issubclass(type(cls), ModelMetaclass)
    )
    return pydantic_classes


def _write_json_schemas(
        output_dir: Path, classes: Iterable[ModelMetaclass], package_name: str
) -> None:
    """Writes JSON-schemas for classes in YAML."""
    try:
        output_dir.mkdir()
    except FileExistsError:
        pass

    for cls in classes:
        if hasattr(cls, "schema_json"):
            filename = cls.__module__.replace(package_name + '.', '').rsplit(sep='.',
                                                                             maxsplit=1)[
                           0]+"."+cls.__name__+".yml"
            data = json.loads(cls.schema_json())
            with open(filename, "w") as file:
                yaml.dump(data, file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--package", help="Package containing models for which "
                                                "json-schema will be generated",
                        default="visiobas_gateway.models")
    args = parser.parse_args()

    pydantic_models = _get_pydantic_classes(package_name=args.package)
    _write_json_schemas(output_dir=DOCS_DIR, classes=pydantic_models, package_name=args.package)

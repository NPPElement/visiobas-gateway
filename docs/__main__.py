import json
from pathlib import Path
from typing import Iterable

import yaml
from pydantic.main import ModelMetaclass

from visiobas_gateway import DOCS_DIR

PACKAGE_NAME = "visiobas_gateway.models"


def get_pydantic_classes(package_name: str) -> Iterable[ModelMetaclass]:
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


def generate_schema_definition(
    output_dir: Path, classes: Iterable[ModelMetaclass], package_name: str
):
    try:
        output_dir.mkdir()
    except FileExistsError:
        pass

    for cls in classes:
        # if hasattr(cls, "schema_json"):
        data = json.loads(cls.schema_json())
        path_in_package = (
            cls.__module__.replace(package_name + ".", "") + "." + cls.__name__ + ".yml"
        )
        print("PATH_IN_PACKAGE", path_in_package)
        with open(path_in_package, "w") as file:
            yaml.dump(data, file)
        # print(cls.__name__, cls.__module__, cls.schema_json())


if __name__ == "__main__":
    pydantic_models = get_pydantic_classes(package_name=PACKAGE_NAME)
    generate_schema_definition(
        output_dir=DOCS_DIR, classes=pydantic_models, package_name=PACKAGE_NAME
    )

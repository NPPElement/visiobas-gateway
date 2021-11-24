import pip

from run import check_root, run_cmd_with_check
from run.install import DOCKER_COMPOSE_YAML_PATH, INSTALL_DIRECTORY

GATEWAY_REPOSITORY_URL = "https://github.com/NPPElement/visiobas-gateway"

DOCKER_COMPOSE_GATEWAY_ALIAS = "vb_gateway"

BUILD_CONTEXT = INSTALL_DIRECTORY
DOCKERFILE_NAME = "DOCKERFILE"

if __name__ == "__main__":
    check_root()
    try:
        run_cmd_with_check("docker-compose up %s" % DOCKER_COMPOSE_YAML_PATH)
    except RuntimeError:
        choice = input(
            "VisioBAS Gateway container RUN FAILED. "
            "Would you like build container? (y/n): "
        ).lower()
        if choice not in {"y", "yes", "true", "1"}:
            exit()

        run_cmd_with_check("apt-get install -y git")
        run_cmd_with_check("git clone %s" % GATEWAY_REPOSITORY_URL)
        pip.main(["install", "pyyaml"])
        import yaml

        with open(DOCKER_COMPOSE_YAML_PATH, "r") as f:
            docker_compose_dict = yaml.safe_load(f)

        service_section = docker_compose_dict["services"][DOCKER_COMPOSE_GATEWAY_ALIAS]
        service_section.pop(["image"])
        service_section["build"] = {
            "context": BUILD_CONTEXT,
            "dockerfile": DOCKERFILE_NAME,
        }
        docker_compose_dict["services"][DOCKER_COMPOSE_GATEWAY_ALIAS] = service_section

        print("\n`%s` has been modified for build image.\n" % DOCKER_COMPOSE_YAML_PATH)

        with open(DOCKER_COMPOSE_YAML_PATH, "w") as f:
            yaml.dump(docker_compose_dict, DOCKER_COMPOSE_YAML_PATH)

        run_cmd_with_check("docker-compose up %s --build" % DOCKER_COMPOSE_YAML_PATH)

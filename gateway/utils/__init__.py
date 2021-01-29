from os import environ

from gateway.http import VisioHTTPNode


def read_cfg_from_env() -> dict:
    """
    :return: Config, read from environment variables
    """

    try:
        get_node = VisioHTTPNode.read_from_env(main_var_root='GET')
        post_nodes = []

        i = 0
        while True:
            try:
                var_root = f'POST_{i}'
                post_server_data = VisioHTTPNode.read_from_env(main_var_root=var_root)
                post_nodes.append(post_server_data)
                i += 1

            except EnvironmentError:
                break

        config = {
            'http': {
                'get_node': get_node,
                'post_nodes': post_nodes,
                'delay_attempt': environ.get('HTTP_DELAY_RECONNECT', 30),  # todo
                'delay_no_objects': environ.get('DELAY_NO_OBJECTS', 60),  # todo
                # TODO implement backoff: https://habr.com/ru/post/227225/
                'get_period': environ.get('HTTP_GET_PERIOD', 60 * 60)  # todo
            },
            'bacnet_verifier': {
                'http_enable': True if environ.get(
                    'HTTP_ENABLE', 'false').lower() == 'true' else False,
                'mqtt_enable': True if environ.get(
                    'MQTT_ENABLE', 'false').lower() == 'true' else False,
            },
            'bacnet': {
                'default_update_period': int(
                    environ.get('BACNET_DEFAULT_UPDATE_PERIOD', 10))
            },
            'modbus': {
                'default_update_period': int(
                    environ.get('MODBUS_DEFAULT_UPDATE_PERIOD', 10))
            }
        }
    except EnvironmentError:
        raise EnvironmentError(
            "Please ensure environment variables are set to: \n"
            "'HTTP_{server}_HOST'\n'HTTP_{server}_PORT'\n"
            "'HTTP_{server}_LOGIN'\n'HTTP_{server}_PASSWORD'\nfor each server.\n\n"

            "Also you can provide optional variables: \n"
            "'HTTP_PORT' by default = 8080\n"
            "'HTTP_ENABLE' by default = FALSE\n"
            "'MQTT_ENABLE' by default = FALSE\n"
            "'BACNET_DEFAULT_UPDATE_PERIOD' by default = 10\n"
            "'MODBUS_DEFAULT_UPDATE_PERIOD' by default = 10\n"
        )
    else:
        return config

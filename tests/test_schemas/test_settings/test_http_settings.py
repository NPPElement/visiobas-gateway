from visiobas_gateway.schemas.settings import HTTPSettings
from visiobas_gateway import BASE_DIR


class TestMQTTSettings:
    def test_load_template_env(self):
        """Tests that template is actual."""
        from dotenv import load_dotenv

        template_path = BASE_DIR.parent / "config/template.env"
        load_dotenv(dotenv_path=template_path)
        isinstance(HTTPSettings(), HTTPSettings)

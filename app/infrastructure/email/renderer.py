from pathlib import Path
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).parent / "templates"

_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)


def render_template(template_name: str, **context) -> str:
    template = _env.get_template(template_name)
    return template.render(**context)

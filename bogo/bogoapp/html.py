import logging
import jinja2


logger = logging.getLogger("JinjaWrapper")


class JinjaWrapper:

    def __init__(self, template_path=None):
        if template_path is None:
            loader = jinja2.PackageLoader("bogoapp", "templates")
        else:
            loader = jinja2.FileSystemLoader(template_path)
        self.env = jinja2.Environment(loader=loader, enable_async=True)

    async def render(self, template_name, context):
        if context is None:
            context = {}
        template = self.env.get_template(template_name)
        return await template.render_async(**context)

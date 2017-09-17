import asyncio
import sys
import logging

import sanic

from bogoapp import util


logging_format = ("%(asctime)s %(process)d-%(levelname)s "
                  "%(module)s::%(funcName)s():l%(lineno)d: "
                  "%(message)s")
logging.basicConfig(format=logging_format, level=logging.DEBUG)

# Globals
logger = logging.getLogger(__name__)
logger.debug("Creating globals")

app = util.make_sanic(__name__)
bogo_manager = util.make_bogo_manager()
db_app = util.make_database_manager()
ws_app = util.make_websocket_app(app, bogo_manager.get_current_state)
jinja_app = util.make_jinja_app()

logger.debug("Created all globals")


async def template_response(name, context=None):
    return sanic.response.html(await jinja_app.render(name, context))

@app.route("/")
async def index(request):
    return await template_response("index.html")

@app.route("/about")
async def about(request):
    return await template_response("about.html")

@app.listener("before_server_start")
async def begin_sort(app, loop):
    logging.info("Starting sort")
    bogo_manager.asyncio_task = asyncio.ensure_future(bogo_manager.run())

@app.listener("after_server_stop")
async def abort_sort(app, loop):
    """Graceful abort which saves the state correctly."""
    logging.info("Stopping sort")
    bogo_manager.stopping = True
    await asyncio.wait([bogo_manager.asyncio_task], loop=loop)
    logging.info("Sorting stopped")


if __name__ == "__main__":
    if sys.version_info < (3, 6):
        print("This app requires Python 3.6 or newer.", file=sys.stderr)
        sys.exit(1)
    app.run()
    logging.info("Exiting app")


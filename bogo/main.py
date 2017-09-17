import asyncio
import sys
import logging

import sanic

from bogoapp import util
from bogoapp import bogo


logging_format = ("%(asctime)s %(process)d-%(levelname)s "
                  "%(module)s::%(funcName)s():l%(lineno)d: "
                  "%(message)s")
logging.basicConfig(format=logging_format, level=logging.DEBUG)

# Globals
logger = logging.getLogger(__name__)
logger.debug("Creating globals")

app = util.make_sanic(__name__)
database = util.make_database_manager()
bogo_manager = util.make_bogo_manager(database)
ws_app = util.make_websocket_app(app, bogo_manager.get_current_state)
jinja_app = util.make_jinja_app()

logger.debug("Created all globals")


async def template_response(name, context=None):
    return sanic.response.html(await jinja_app.render(name, context))


async def get_bogo_by_id_or_404(bogo_id):
    bogo_row = await database.bogo_by_id(bogo_id)
    if not bogo_row:
        raise sanic.exceptions.abort(404)
    return bogo.Bogo.from_database_row(bogo_row)

async def adjacent_bogos(bogo_obj):
    older, newer = await database.adjacent_bogos(bogo_obj)
    return (bogo.Bogo.from_database_row(older) if older else None,
            bogo.Bogo.from_database_row(newer) if newer else None)

def url_for_bogo(bogo_id):
    return app.url_for("view_bogo", bogo_id=bogo_id)


@app.route("/")
async def index(request):
    return await template_response("index.html")

@app.route("/about")
async def about(request):
    return await template_response("about.html")

@app.route("/bogo/<bogo_id:int>")
async def view_bogo(request, bogo_id):
    data_url = app.url_for("bogo_json", bogo_id=bogo_id)
    render_context = {"bogo_id":  bogo_id,
                      "data_url": data_url}
    return await template_response('index.html', render_context)

@app.route("/bogo/<bogo_id:int>.json")
async def bogo_json(request, bogo_id):
    bogo = await get_bogo_by_id_or_404(bogo_id)
    stats = {
        'links': {'self': url_for_bogo(bogo_id)},
        'data': bogo.as_dict()
    }
    prev_bogo, next_bogo = await adjacent_bogos(bogo)
    if prev_bogo:
        stats['links']['previous'] = url_for_bogo(prev_bogo.db_id)
    if next_bogo:
        stats['links']['next'] = url_for_bogo(next_bogo.db_id)
    return sanic.response.json(stats)


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


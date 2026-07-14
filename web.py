from aiohttp import web

async def handle(request):
    return web.Response(text="Bot is running")

def start_web():
    app = web.Application()
    app.router.add_get('/', handle)
    web.run_app(app, host='0.0.0.0', port=8080)

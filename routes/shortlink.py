from ihautils.utils import ihaSanic, generate_custom_code
from sanic.views import HTTPMethodView
from sanic.response import text


class ShortlinkAPI(HTTPMethodView):
    async def post(self, request):
        app: ihaSanic = request.app
        appc = app.config
        url_data = request.form.get("url")
        if not url_data:
            return text("No URL provided", 400)

        if not app.validate_url(url_data):
            return text("Invalid URL format.", 400)

        async def _generate_filename():
            while True:
                filename = generate_custom_code(appc["FILENAME_LENGTH"], True)
                if filename in ["upload", "short", "ping"]:
                    continue
                check_data = await app.dcache.get(filename)
                if check_data is None:
                    break
            return filename

        user_ip = request.remote_addr or request.ip

        short_link = await _generate_filename()
        final_url = "https" if appc["HTTPS_MODE"] else "http"
        final_url += f"://{appc['HOST_NAME']}/{short_link}"
        await app.dcache.set(short_link, {"type": "short", "target": url_data})
        await app.announce_discord(user_ip, final_url, False, True)
        return text(final_url)

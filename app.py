import os

from jinja2 import Environment, PackageLoader
from sanic.exceptions import abort
from sanic.log import logger
from sanic.response import file_stream, html, redirect, text

from ihautils.ihacache import ihateanimeCache
from ihautils.utils import generate_custom_code, ihaSanic, read_files, humanbytes
from routes.file_upload import UploadAPI
from routes.shortlink import ShortlinkAPI

env = Environment(loader=PackageLoader("app", "templates"))
app_cwd = os.getcwd()

app = ihaSanic("ihacdn")
settings = dict(
    HOST_NAME="p.ihateani.me",
    HTTPS_MODE=True,
    DISKCACHE_PATH="./diskcache",  # Modify this
    UPLOAD_PATH=os.path.join(app_cwd, "uploads"),
    ADMIN_PASSWORD="MODIFY_THIS",
    FILENAME_LENGTH=8,
    # File retention settings
    ENABLE_FILE_RETENTION=True,  # If enabled, file will be deleted with calculation.
    FILE_RETENTION_MIN_AGE=30,  # Minimum days for file retention.
    FILE_RETENTION_MAX_AGE=180,  # Maximum days for file retention.
    # Storage settings
    FILESIZE_LIMIT=50 * 1024,  # 50mb (in kb.)
    FILESIZE_LIMIT_ADMIN=None,  # Set to None for no limit.
    BLACKLISTED_EXTENSION=["exe", "sh", "msi", "bat", "dll", "com"],
    BLACKLISTED_CONTENT_TYPE=[
        "application/vnd.microsoft.portable-executable",
        "application/x-msi",
        "application/x-msdos-program",
        "application/x-sh",
    ],
)
app.config.update(settings)
app.jinja2env = env
app.config.FORWARDED_SECRET = "wjwhjzppqzemf3wn8v6fkk2arptwng6s"  # Used for reverse proxy


def render_template(template_name: str, *args, **kwargs):
    """Render HTML webpage from a template.

    :param template_name: html name from defined templates folder
    :type template_name: str
    :return: HTML Response ready.
    :rtype: HTTPResponse
    """
    html_template = app.jinja2env.get_template(template_name)
    rendered = html_template.render(*args, **kwargs)
    return html(rendered)


@app.listener("before_server_start")
async def initiated_application(app: ihaSanic, loop):
    logger.info("[beforestart] setting up diskcache...")
    iha_path = app.config.get("DISKCACHE_PATH", "./diskcache")
    if not os.path.isdir(iha_path):
        os.mkdir(iha_path)
    cache = ihateanimeCache(iha_path, loop)
    await cache.ping()
    if not cache.is_usable:
        logger.error("[beforestart] failed to setup diskcache.")
    else:
        logger.info("[beforestart] binding to app.")
        app.dcache = cache
    if not os.path.isdir(app.config["UPLOAD_PATH"]):
        logger.info("[beforestart] creating upload folder.")
        os.makedirs(app.config["UPLOAD_PATH"])
    app.config.update(dict(UPLOAD_PATH_ADMIN=app.config["UPLOAD_PATH"].rstrip("/").rstrip("\\") + "_admin"))
    if not os.path.isdir(app.config["UPLOAD_PATH_ADMIN"]):
        logger.info("[beforestart] creating persistence/admin upload folder.")
        os.makedirs(app.config["UPLOAD_PATH_ADMIN"])


# static_file_bp = Blueprint("uploads", url_prefix="/")
# static_file_bp.static("./uploads")
# app.register_blueprint(static_file_bp)

app.add_route(UploadAPI.as_view(), "/upload")
app.add_route(ShortlinkAPI.as_view(), "/short")

app.static(
    "/static/atom-one-dark.css", "./static/atom-one-dark.css", content_type="text/css",
)
app.static(
    "/static/highlightjs-line-numbers.min.js",
    "./static/highlightjs-line-numbers.min.js",
    content_type="text/javascript; charset=utf-8",
)
app.static(
    "/static/highlight.pack.js", "./static/highlight.pack.js", content_type="text/javascript; charset=utf-8",
)

app.static("/favicon.ico", "./static/ihaBadge.ico", content_type="image/x-icon")
app.static("/favicon.png", "./static/ihaBadge.png", content_type="image/png")


@app.route("/<file_path:path>")
async def check_path(request, file_path):
    extract_path = os.path.splitext(os.path.basename(file_path))
    filename, ext = None, None
    try:
        filename = extract_path[0]
        ext = extract_path[1]
    except IndexError:
        abort(404)
    logger.info(f"trying to access: {filename}")
    get_data = await app.dcache.get(filename)
    if get_data is None:
        logger.error(f"key {filename} not found.")
        abort(404)
    if get_data["type"] == "code":
        logger.info(f"key {filename} are code type, using html format.")
        code_contents = await read_files(get_data["path"], True)
        if code_contents is None:
            await app.dcache.delete(filename)
            abort(410)
        snip_code = code_contents[:10]
        html_template = app.jinja2env.get_template("textcode.html")
        logger.info("rendering code...")
        rendered = html_template.render(
            filename=filename,
            snippets=snip_code,
            code_data=code_contents,
            determine_type="" if ext is None else ext.strip("."),
        )
        return html(rendered)
    elif get_data["type"] == "short":
        logger.info(f"key {filename} are short link, redirecting to: {get_data['target']}.")
        return redirect(get_data["target"])
    elif get_data["type"] == "file":
        logger.info(f"key {filename} are file type, sending file.")
        try:
            return await file_stream(get_data["path"], mime_type=get_data["mimetype"])
        except Exception:
            await app.dcache.delete(filename)
            abort(410)
    abort(404)


@app.post("/populate")
async def populate_db(request):
    import glob

    import magic

    passkey = request.form.get("passkey")
    clean = request.form.get("clean", 0)
    if not passkey:
        return text("Please provide admin password.", 403)
    if isinstance(passkey, list):
        passkey = passkey[0]
    if passkey != app.config["ADMIN_PASSWORD"]:
        return text("Please enter correct password.", 401)
    if clean:
        await app.dcache.expire()

    async def _generate_filename():
        while True:
            filename = generate_custom_code(app.config["FILENAME_LENGTH"], True)
            if filename in ["upload", "short", "ping"]:
                continue
            check_data = await app.dcache.get(filename)
            if check_data is None:
                break
        return filename

    logger.info("[populate] collecting data...")
    globbed_files = glob.glob(os.path.join(app.config["UPLOAD_PATH"], "*"))
    logger.info(f"[populate] total data: {len(globbed_files)}...")
    bmagic = magic.Magic(mime=True)
    for fpath in globbed_files:
        file_name_ext = os.path.basename(fpath)
        file_name = ".".join(file_name_ext.split(".")[0:-1])
        extension = file_name_ext.split(".")[-1]
        mimetype = bmagic.from_file(fpath)
        is_code = False
        if mimetype.startswith("text"):
            is_code = True
        check_key = await app.dcache.get(file_name)
        if check_key:
            logger.warning(f"[populate] rerouting: {file_name} ({fpath})")
            file_name = await _generate_filename()
            new_fn = f"{file_name}.{extension}"
            new_fpath = os.path.join(app.config["UPLOAD_PATH"], new_fn)
            os.rename(fpath, new_fpath)
            fpath = new_fpath
        logger.info(f"[populate] adding: {file_name} ({fpath})")
        await app.dcache.set(
            file_name,
            {
                "type": "code" if is_code else "file",
                "path": fpath,
                "mimetype": extension if is_code else mimetype,
            },
        )
    return text("Done populating.")


@app.route("/")
async def home_page(request):
    return render_template(
        "home.html",
        HOST_NAME=app.config.HOST_NAME,
        HTTPS_MODE=app.config.HTTPS_MODE,
        FSIZE_LIMIT=humanbytes(
            app.config.FILESIZE_LIMIT * 1024 if app.config.FILESIZE_LIMIT is not None else None
        ),
        BLACKLIST_EXTENSION=app.config.BLACKLISTED_EXTENSION,
        BLACKLIST_CTYPES=app.config.BLACKLISTED_CONTENT_TYPE,
    )


if __name__ == "__main__":
    logger.info("Starting server...")
    logger.info(f"Super secret forwarding code: {app.config.FORWARDED_SECRET}")
    app.run(host="127.0.0.1", port=6900, debug=False, access_log=True)

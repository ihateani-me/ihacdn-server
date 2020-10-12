import os

import magic
from ihautils.utils import generate_custom_code, ihaSanic, write_files
from sanic.response import text
from sanic.exceptions import abort
from sanic.views import HTTPMethodView


def valid_file_type(file_name, file_type, blacklist_ext, blacklist_ctypes):
    file_name_type = file_name.split(".")[-1]
    if file_name_type in blacklist_ext:
        return False, file_name_type
    if file_type in blacklist_ctypes:
        return False, file_type
    return True, file_name_type


def do_use_code_template(file_type):
    if file_type.startswith("text"):
        return True
    return False


def valid_file_size(file_body, limit):
    if limit is None:
        return True
    if len(file_body) < limit * 1024:
        return True
    return False


class UploadAPI(HTTPMethodView):
    async def post(self, request):
        app: ihaSanic = request.app
        appc = app.config
        upload_file = request.files.get("file")
        if not upload_file:
            return text("No file provided", 400)
        bmagic = magic.Magic(mime=True)
        password = request.form.get("secret", "")
        if isinstance(password, list):
            password = password[0]
        is_admin = False
        if password == app.config["ADMIN_PASSWORD"]:
            is_admin = True
        mimetype = bmagic.from_buffer(upload_file.body)

        async def _generate_filename():
            while True:
                filename = generate_custom_code(appc["FILENAME_LENGTH"], True)
                if filename in ["upload", "short", "ping"]:
                    continue
                check_data = await app.dcache.get(filename)
                if check_data is None:
                    break
            return filename

        filename = await _generate_filename()
        file_name_type = upload_file.name.split(".")[-1]
        is_valid_type, invalid_type_data = valid_file_type(
            upload_file.name, mimetype, appc["BLACKLISTED_EXTENSION"], appc["BLACKLISTED_CONTENT_TYPE"],
        )
        if not is_valid_type and not is_admin:
            abort(415, invalid_type_data)

        fs_limit = appc["FILESIZE_LIMIT"] if not is_admin else appc["FILESIZE_LIMIT_ADMIN"]
        if not valid_file_size(upload_file.body, fs_limit):
            abort(413, upload_file.name)

        is_code = do_use_code_template(mimetype)
        final_url = "https" if appc["HTTPS_MODE"] else "http"
        final_url += f"://{appc['HOST_NAME']}/{filename}.{file_name_type}"
        file_path = os.path.join(appc["UPLOAD_PATH"], f"{filename}.{file_name_type}")
        if is_admin:
            file_path = os.path.join(appc["UPLOAD_PATH_ADMIN"], f"{filename}.{file_name_type}")
        code_type = file_name_type
        if not is_code:
            await write_files(upload_file.body, file_path)
        else:
            code_data = upload_file.body.decode("utf-8").replace("\r\n", "\n")
            await write_files(code_data, file_path)
        await app.dcache.set(
            filename,
            {
                "type": "code" if is_code else "file",
                "path": file_path,
                "mimetype": code_type if is_code else upload_file.type,
            },
        )
        return text(final_url)

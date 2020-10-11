# ihaCDN

![Status](https://img.shields.io/uptimerobot/status/m784617086-4e68d7e9dd7670f5c03bc09b?label=Status&style=for-the-badge) ![Uptime (7 days)](https://img.shields.io/uptimerobot/ratio/7/m784617086-4e68d7e9dd7670f5c03bc09b?style=for-the-badge)

A simple file hosting using Sanic framework.<br>
**Currently running on: [https://p.ihateani.me/](https://p.ihateani.me/)**

## Feature

- Image/Files/Text support with blacklisting.
- Auto determining if it's text or files without user defining itself.
- Filesize limit support. **[Can be disabled.]**
- [Customizable](#configuration).
- Code highlighting support using **highlight.js**
- Shortlink generation support.
- You don't need the extension to access your files/code.
- You could manually set what hljs should use by adding extension to the url.

## Using the filehosting.
There's 2 POST endpoint:
- `/upload` for image/files/text
- `/short` for shortening link.

To upload, you need to provide file with the name `file`.<br>
To shorten url, you need to use form data with `url` as the key.

**Example with curl**:<br>
Uploading files:<br>
```bash
curl -X POST -F "file=@yourfile.png" https://p.ihateani.me/upload
```

Shortening link:<br>
```bash
curl -X POST -F "url=http://your.long/ass/url/that/you/want/to/shorten" https://p.ihateani.me/short
```

Or you could use [ShareX](https://getsharex.com/) and import the provided [sxcu](https://github.com/noaione/ihacdn-server/tree/master/sharex) files.

## Setup
**Requirements**:
- Python 3.6+
- Sanic
- jinja2
- aiofiles
- ujson==1.35
- diskcache
- python-magic


1. Download this repo by either cloning or downloading it.
2. Install Python 3.6+
3. Create a new Virtual Environment `virtualenv ihaEnv` then activate it.
4. Install all requirements via `pip install -r requirements.txt`
5. Install libmagic, you can refer to [here](https://github.com/ahupp/python-magic#installation) to install it.
6. Run it: `python app.py`
7. The app will be deployed on http://127.0.0.1:6900/

## Configuration
Configure this program by opening `app.py`<br>
You will see a `settings` variable.

```py
settings = dict(
    HOST_NAME="p.ihateani.me",
    HTTPS_MODE=True,
    DISKCACHE_PATH="./diskcache",  # Modify this
    UPLOAD_PATH=os.path.join(app_cwd, "uploads"),
    ADMIN_PASSWORD="MODIFY_THIS",
    FILENAME_LENGTH=8,
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
```

That's the default settings, you can adjust it what you want.

Explanation:
- **HOST_NAME**: are your web domain.
- **HTTPS_MODE**: is your website gonna run on https or not.
- **DISKCACHE_PATH**: where to put your cache data (or the database of the app)
- **UPLOAD_PATH**: where to put your uploads path.
- **ADMIN_PASSWORD**: admin password, please modify this.
- **FILENAME_LENGTH**: the randomized filename length.
- **FILESIZE_LIMIT**: upload size limit for normal user. (can be set to `None` for no limit.)
- **FILESIZE_LIMIT_ADMIN**: upload size limit for someone using admin. (can be set to `None` for no limit.)
- **BLACKLISTED_EXTENSION**: Blacklisted extension.
- **BLACKLISTED_CONTENT_TYPE**: Blacklisted content-type.

## Deploying on Nginx.

Refer to Sanic documentation to deploy on Nginx: [https://sanic.readthedocs.io/en/latest/sanic/nginx.html](https://sanic.readthedocs.io/en/latest/sanic/nginx.html)

And then, on this line:
```py
    # Proxy forwarding (password configured in app.config.FORWARDED_SECRET)
    proxy_set_header forwarded "$proxy_forwarded;secret=\"YOUR SECRET\"";
```

Change `YOUR SECRET` into `wjwhjzppqzemf3wn8v6fkk2arptwng6s`.

It's also recommended to set `client_max_body_size` to make sure you can upload large files.<br>
You can either put it on `http` block on `/etc/nginx/nginx.conf` or the `server` block on `sites-available` conf.

Example:
```py
http {
    ...
    client_max_body_size 1024M; # This will set the limit to 1 GiB.
    ...
}
```

## External library acknowledgements.
This project use [highlight.js](https://github.com/highlightjs/highlight.js/) for code highlighting.<br>
This project also use [highlightjs-line-numbers](https://github.com/wcoder/highlightjs-line-numbers.js/) to add line numbers to generated highlighted code.

*This project is licensed with MIT License*
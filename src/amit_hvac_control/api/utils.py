from aiohttp import MultipartWriter


def get_multipart_data(post: dict):
    with MultipartWriter("form-data") as mp:
        for key, value in post.items():
            part = mp.append(str(value))

            del part.headers["Content-Type"]
            part.set_content_disposition("form-data", name=key)
        return mp

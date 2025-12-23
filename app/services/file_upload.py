import os
from fastapi import UploadFile, HTTPException

UPLOAD_DIR = "app/static/uploads"
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
}
ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".gif"}

os.makedirs(UPLOAD_DIR, exist_ok=True)


async def save_image_file(
    image: UploadFile,
    filename: str,
) -> str | None:
    """
    画像ファイルを検証して保存する
    成功時: 保存ファイル名
    失敗時: HTTPException
    """

    if not image or not image.filename:
        return None

    if image.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="画像形式は jpg / png / gif のみ対応しています"
        )

    content = await image.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="画像サイズは2MB以内にしてください"
        )

    _, ext = os.path.splitext(image.filename)
    if ext.lower() not in ALLOWED_EXTS:
        raise HTTPException(
            status_code=400,
            detail="ファイル種別が不正です"
        )

    save_path = os.path.join(UPLOAD_DIR, filename)
    with open(save_path, "wb") as f:
        f.write(content)

    return filename
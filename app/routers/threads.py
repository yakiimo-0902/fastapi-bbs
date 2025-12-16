from fastapi import APIRouter,Depends, HTTPException, Request
from app.models.thread import Thread
from app.models.post import Post

from app.schemas.thread import ThreadResponse, ThreadCreate
from app.database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import select, insert,func

router = APIRouter(
    prefix="/threads",
    tags=["Threads"]
)

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import aliased

templates = Jinja2Templates(directory="app/templates")
# -----------------------------------
# フロント側処理 詳細
# -----------------------------------
@router.get("/{thread_id}/view", response_class=HTMLResponse)
async def threads_detail_page(request: Request, thread_id: int,page:int=1 , db: Session = Depends(get_db)):
    ParentPost = aliased(Post)   # ← Post の別名（親投稿用）
    limit = 10 # page当たりの件数
    offset = (page - 1) * limit # 何件目から何件目を取得するか
    
# ───────────────
    # ① 最初の投稿（post_number=1）を取得（固定表示）
    # ───────────────
    ParentPost = aliased(Post)
    stmt_first = (
        select(
            Post.id,
            Post.content,
            Post.author,
            Post.created_at,
            Post.attachment,
            Post.post_number,
            ParentPost.post_number.label("parent_post_number")
        )
        .outerjoin(ParentPost, ParentPost.id == Post.parent_post_id)
        .where(Post.thread_id == thread_id, Post.post_number == 1)
    )
    first_post = db.execute(stmt_first).first()

    # ───────────────
    # ② 2番目以降の投稿をページネーション
    # ───────────────
    stmt_posts = (
        select(
            Post.id,
            Post.content,
            Post.author,
            Post.created_at,
            Post.attachment,
            Post.post_number,
            ParentPost.post_number.label("parent_post_number")
        )
        .outerjoin(ParentPost, ParentPost.id == Post.parent_post_id)
        .where(Post.thread_id == thread_id, Post.post_number > 1)
        .order_by(Post.post_number.asc())
        .limit(limit)
        .offset(offset)
    )

    posts = db.execute(stmt_posts).all()

    # ───────────────
    # ③ 全件数を取得して総ページ数を算出
    # ───────────────
    stmt_count = select(func.count()).where(
        Post.thread_id == thread_id,
        Post.post_number > 1
    )
    total_posts = db.execute(stmt_count).scalar_one()
    total_pages = (total_posts + limit - 1) // limit

    return templates.TemplateResponse(
        "thread_detail.html",
        {
            "request": request,
            "first_post": first_post,
            "posts": posts,
            "thread_id": thread_id,
            "page": page,
            "total_pages": total_pages,
        }
    )


# -----------------------------------
# フロント側処理 スレッドの新規作成画面を表示
# -----------------------------------
@router.get("/new", response_class=HTMLResponse)
async def new_thread_page(request: Request):
    return templates.TemplateResponse("new_thread.html", {"request": request})


# -----------------------------------
# フロント側処理 スレッドの新規作成
# -----------------------------------
from fastapi import Form, File, UploadFile, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import insert, select
from sqlalchemy.orm import Session
from app.models.thread import Thread
from app.models.post import Post
from app.database import get_db
import os

UPLOAD_DIR = "app/static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/create")
async def create_thread_front(
    request: Request,
    title: str = Form(...),
    author: str = Form(""),
    content: str = Form(...),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db)):

    # (1) Thread 作成
    stmt = insert(Thread).values(title=title)
    result = db.execute(stmt)
    db.commit()
    new_thread_id = result.lastrowid

    # (1.5)添付ファイル処理
    attachment_filename = None
    if image and image.filename:
        # ファイル名の決定
        _,ext = os.path.splitext(image.filename)
        filename = f"thread{new_thread_id}_post1{ext}"
        save_path = os.path.join(UPLOAD_DIR,filename)

        # 保存
        with open(save_path,"wb") as f:
            f.write(await image.read())
        attachment_filename = filename


    # (2) Post（本文）作成
    values = {
        "thread_id": new_thread_id,
        "content": content,
        "post_number":1,
    }

    # author 空欄なら DEFAULT '名無しさん' を使う
    if author.strip():
        values["author"] = author

    # 添付ファイルがあれば追加
    if attachment_filename:
        values["attachment"] = attachment_filename

    db.execute(insert(Post).values(values))
    db.commit()

    # (3) スレッド詳細へリダイレクト
    return RedirectResponse(
        url=f"/threads/{new_thread_id}/view",
        status_code=303
    )


from sqlalchemy import select, insert,func
# -----------------------------------
# フロント側処理 一覧（ページネーション対応）
# -----------------------------------
@router.get("/list", response_class=HTMLResponse)
async def list_threads_page(
    request: Request, 
    page: int = 1, 
    db: Session = Depends(get_db)
):

    limit = 20  # 1ページあたりの件数
    offset = (page - 1) * limit

    # -----------------------------------
    # ① スレッド一覧（ページネーション付き）
    # -----------------------------------
    stmt_threads = (
        select(Thread)
        .order_by(Thread.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    threads = db.execute(stmt_threads).scalars().all()

    # -----------------------------------
    # ② スレッド総数を取得 → ページ数算出
    # -----------------------------------
    stmt_count = select(func.count()).select_from(Thread)
    total_threads = db.execute(stmt_count).scalar_one()
    total_pages = (total_threads + limit - 1) // limit

    # -----------------------------------
    # ③ 最新投稿10件（これはそのまま）
    # -----------------------------------
    stmt_posts = (
        select(
            Post.id,
            Post.content,
            Post.author,
            Post.created_at,
            Post.attachment,
            Post.post_number,
            Thread.title.label("thread_title"),
            Thread.id.label("thread_id"),
        )
        .join(Thread, Thread.id == Post.thread_id)
        .order_by(Post.created_at.desc())
        .limit(10)
    )
    latest_posts = db.execute(stmt_posts).all()

    # -----------------------------------
    # ④ テンプレートへ渡す
    # -----------------------------------
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "threads": threads,
            "latest_posts": latest_posts,
            "page": page,
            "total_pages": total_pages,
        }
    )

# -----------------------------------
# スレッド一覧 GET /threads
# -----------------------------------
@router.get("/", response_model=list[ThreadResponse])
async def list_threads(db: Session = Depends(get_db)):
    stmt = select(Thread)
    result = db.execute(stmt).scalars().all()
    return result

# -----------------------------------
# スレッド詳細 GET /threads/{thread_id}
# -----------------------------------
@router.get("/{thread_id}", response_model=ThreadResponse)
async def get_thread(thread_id: int, db: Session = Depends(get_db)):
    stmt = select(Thread).where(Thread.id == thread_id)
    result = db.execute(stmt).scalar_one_or_none()

    if result is None:
        # 見つからないので例外を raise 404 Not found
        raise HTTPException(status_code=404, detail="Thread not found")

    return result

# -----------------------------------
# スレッド作成 POST /threads
# -----------------------------------
@router.post("/", response_model=ThreadResponse)
async def create_thread(thread: ThreadCreate,db: Session = Depends(get_db)):
    # INSERT
    stmt = insert(Thread).values(title=thread.title)
    result = db.execute(stmt)
    db.commit()

    # 実行結果からidを取得(AUTOINCREMENT で生成された id を取得)
    new_id = result.lastrowid

    # 今作ったレコードを読み直し
    stmt2 = select(Thread).where(Thread.id == new_id)
    new_thread = db.execute(stmt2).scalar_one()
    return new_thread

# -----------------------
# ダミー投稿作成
# POST /threads/gen_dummy_threads
# -----------------------
from faker import Faker
fake = Faker("ja_JP")   # 日本語のデータを生成

@router.post("/gen_dummy_threads")
def generate_dummy_threads(
    count: int = 100,               # ← デフォルト100件
    db: Session = Depends(get_db)
):
    created_ids = []

    for _ in range(count):
        # ---------------------------------
        # ① Thread 作成
        # ---------------------------------
        title = fake.sentence(nb_words=5)

        stmt_thread = insert(Thread).values(title=title)
        result = db.execute(stmt_thread)
        thread_id = result.lastrowid

        # ---------------------------------
        # ② Post（最初の投稿 = post_number=1）
        # ---------------------------------
        content = fake.text(max_nb_chars=120)

        stmt_post = insert(Post).values(
            thread_id=thread_id,
            content=content,
            post_number=1,
            author=fake.name(), # fakerライブラリ使用
        )
        db.execute(stmt_post)

        created_ids.append(thread_id)

    db.commit()

    return {
        "status":"ok",
        "created_threads": len(created_ids),
        "thread_ids": created_ids
    }
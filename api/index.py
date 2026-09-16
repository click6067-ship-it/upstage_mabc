def handler(request):
    from backend.server import app

    asgi_app = app

    # Vercel Python 런타임은 ASGI 앱을 직접 기대하므로,
    # 여기서는 FastAPI app을 그대로 callable로 반환한다.
    return asgi_app

from fastapi.middleware.cors import CORSMiddleware

class MiddlewareSetup:
    def __init__(self, app):
        self.app = app
        self._setup_cors()

    def _setup_cors(self):
        """Setup CORS middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
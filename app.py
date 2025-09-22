import os
import secrets
import base64
from datetime import datetime

from flask import Flask, request, jsonify, Response, make_response
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker


def get_database_url() -> str:
    # Prefer environment DATABASE_URL; fallback to local SQLite for quick start
    return os.environ.get('DATABASE_URL', 'sqlite:///designs.db')


Base = declarative_base()


class Design(Base):
    __tablename__ = 'designs'
    id = Column(Integer, primary_key=True)
    code = Column(String(24), unique=True, nullable=False, index=True)
    product_id = Column(String(255), nullable=False)
    svg = Column(Text, nullable=False)
    state_json = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


def create_app() -> Flask:
    app = Flask(__name__)

    # Basic config
    app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB limit
    app.config['ALLOWED_ORIGIN'] = os.environ.get('ALLOWED_ORIGIN', '*')
    app.config['ADMIN_USER'] = os.environ.get('ADMIN_USER', '')
    app.config['ADMIN_PASS'] = os.environ.get('ADMIN_PASS', '')

    # Database
    engine = create_engine(get_database_url())
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    # Utilities
    def cors_ok(resp: Response) -> Response:
        origin = request.headers.get('Origin')
        allowed = app.config['ALLOWED_ORIGIN']
        # Allow exact origin match or wildcard
        if allowed == '*' or (origin and origin == allowed):
            resp.headers['Access-Control-Allow-Origin'] = origin if origin else '*'
            resp.headers['Vary'] = 'Origin'
            resp.headers['Access-Control-Allow-Credentials'] = 'true'
        return resp

    def require_basic_auth() -> bool:
        # Returns True if authorized
        auth = request.authorization
        return (
            bool(app.config['ADMIN_USER'])
            and bool(app.config['ADMIN_PASS'])
            and auth is not None
            and auth.username == app.config['ADMIN_USER']
            and auth.password == app.config['ADMIN_PASS']
        )

    def generate_code() -> str:
        # URL-safe, short, non-guessable code (8-10 chars)
        return secrets.token_urlsafe(7).replace('-', '').replace('_', '')[:10]

    @app.route('/api/designs', methods=['OPTIONS', 'POST'])
    def save_design():
        # CORS preflight
        if request.method == 'OPTIONS':
            resp = make_response('', 204)
            resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
            resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            return cors_ok(resp)

        # CORS restrict origin if configured
        allowed = app.config['ALLOWED_ORIGIN']
        origin = request.headers.get('Origin')
        if allowed != '*' and origin != allowed:
            return jsonify({ 'error': 'Origin not allowed' }), 403

        data = request.get_json(silent=True) or {}
        product_id = (data.get('productId') or '').strip()
        svg = data.get('svg') or ''
        state = data.get('state')

        if not product_id or not svg:
            return cors_ok(jsonify({ 'error': 'productId and svg are required' })), 400
        if len(svg) > 1_500_000:  # ~1.5MB hard cap
            return cors_ok(jsonify({ 'error': 'SVG too large' })), 413

        session = SessionLocal()
        try:
            # Generate unique code
            code = generate_code()
            # Rare collision handling
            for _ in range(3):
                if session.query(Design).filter_by(code=code).first() is None:
                    break
                code = generate_code()

            design = Design(
                code=code,
                product_id=product_id,
                svg=svg,
                state_json=(state if isinstance(state, str) else None) or (None if state is None else str(state)),
            )
            session.add(design)
            session.commit()
            resp = jsonify({ 'code': code })
            return cors_ok(resp)
        finally:
            session.close()

    @app.route('/d/<code>', methods=['GET'])
    def view_design(code: str):
        # Basic Auth gate if configured
        if app.config['ADMIN_USER'] and app.config['ADMIN_PASS']:
            if not require_basic_auth():
                resp = Response('Authentication required', 401)
                resp.headers['WWW-Authenticate'] = 'Basic realm="Designs"'
                return resp

        session = SessionLocal()
        try:
            design = session.query(Design).filter_by(code=code).first()
            if not design:
                return Response('Code not found', 404)

            # Minimal HTML viewer with inline preview and download
            safe_name = ''.join(ch if ch.isalnum() else '-' for ch in (design.product_id or 'design')).strip('-').lower()
            svg_data_url = 'data:image/svg+xml;base64,' + base64.b64encode(design.svg.encode('utf-8')).decode('ascii')
            html = f"""
<!doctype html>
<html>
  <head>
    <meta charset='utf-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1'>
    <title>Design {code}</title>
    <style>
      body {{ font-family: Arial, Helvetica, sans-serif; margin: 16px; }}
      .wrap {{ max-width: 980px; margin: 0 auto; }}
      .meta {{ color:#666; font-size: 13px; margin-bottom: 8px; }}
      .preview {{ border:1px solid #ddd; border-radius:8px; overflow:auto; background:#fafafa; padding:8px; }}
      .actions {{ margin-top:12px; display:flex; gap:8px; }}
      .btn {{ border:1px solid #ddd; background:#fff; padding:8px 10px; border-radius:6px; text-decoration:none; color:#111; }}
    </style>
  </head>
  <body>
    <div class='wrap'>
      <h2>Design code: {code}</h2>
      <div class='meta'>Product: {design.product_id} · Created: {design.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC</div>
      <div class='preview'>
        <img src='{svg_data_url}' alt='SVG preview' style='max-width:100%; height:auto; display:block;'>
      </div>
      <div class='actions'>
        <a class='btn' href='{svg_data_url}' download='{safe_name}-{code}.svg'>Download SVG</a>
      </div>
    </div>
  </body>
  </html>
            """
            return Response(html, mimetype='text/html')
        finally:
            session.close()

    @app.route('/healthz')
    def healthz():
        return 'ok'

    return app


app = create_app()




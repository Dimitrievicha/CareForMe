from flask import Flask, jsonify, session
from src.backend.web.routes.auth_routes import auth_bp
from src.backend.web.routes.plant_routes import plants_bp
from src.backend.web.routes.plant_routes_dc import plants_dc_bp  # Новый импорт


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'

    app.register_blueprint(auth_bp)
    app.register_blueprint(plants_bp)  # v1 API

    # Регистрируем новые маршруты с датаклассами (v2)
    app.register_blueprint(plants_dc_bp)  # v2 API с датаклассами

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found"}), 404

    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({"status": "healthy"}), 200

    return app
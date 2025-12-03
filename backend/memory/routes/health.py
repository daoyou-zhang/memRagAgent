from flask import jsonify, Blueprint


def register_health_routes(bp: Blueprint) -> None:
    @bp.get("/health")
    def health():
        data = {
            "status": "ok",
            "service": "memory",
            "version": "v0.1.0",
        }
        return jsonify(data)
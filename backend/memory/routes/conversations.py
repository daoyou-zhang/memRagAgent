from flask import Blueprint, jsonify, request

from ..services.conversation_service import record_conversation_service

conversations_bp = Blueprint("conversations", __name__)

@conversations_bp.post("/record")
def record_conversation():
    data = request.get_json() or {}

    user_id = data.get("user_id")
    session_id = data.get("session_id")
    project_id = data.get("project_id")

    if not session_id:
        return jsonify({"error": "session_id is required"}), 400

    raw_query = data.get("raw_query", "")
    optimized_query = data.get("optimized_query")
    intent = data.get("intent", {})
    tool_used = data.get("tool_used")
    tool_result = data.get("tool_result")
    context_used = data.get("context_used", {})
    llm_response = data.get("llm_response", "")
    processing_time = data.get("processing_time", 0)
    auto_generate = data.get("auto_generate_memory", True)

    try:
        result = record_conversation_service(
            user_id=user_id,
            session_id=session_id,
            project_id=project_id,
            raw_query=raw_query,
            optimized_query=optimized_query,
            intent=intent,
            tool_used=tool_used,
            tool_result=tool_result,
            context_used=context_used,
            llm_response=llm_response,
            processing_time=processing_time,
            auto_generate=auto_generate,
        )
        return jsonify(result)
    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e), "type": type(e).__name__}), 500
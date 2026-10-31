from rest_framework.views import exception_handler
def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None
    original = response.data
    if isinstance(original, dict) and "detail" in original:
        message = str(original["detail"])
        errors = {}
    else:
        message = "Validation failed."
        errors = original
    response.data = {
        "success": False,
        "message": message,
        "errors": errors,
    }
    return response
"""Public chat errors never include provider bodies or credentials."""


class ChatError(Exception):
    def __init__(self, code, message, status=400, retryable=False, **details):
        super().__init__(message)
        self.code, self.status, self.retryable = code, status, retryable
        self.details = details

    def public(self):
        return {"code": self.code, "message": str(self), "retryable": self.retryable, **self.details}

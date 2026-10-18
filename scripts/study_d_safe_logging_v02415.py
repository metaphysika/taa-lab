"""vLLM parent/EngineCore durable logging; stdlib only, no backend on import."""
import logging
import os


class RedactingFileHandler(logging.FileHandler):
    def format(self, record):
        text=super().format(record)
        for name in ('HF_TOKEN','MODAL_TOKEN_ID','MODAL_TOKEN_SECRET'):
            value=os.environ.get(name)
            if value:
                text=text.replace(value,'[REDACTED '+name+']')
        return text

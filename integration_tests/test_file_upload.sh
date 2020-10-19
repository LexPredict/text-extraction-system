#!/bin/bash

curl -v --form-string call_back_url=http://localhost:65534 -F file=@docx_simple.pdf http://127.0.0.1:8000/api/v1/text_extraction_tasks/
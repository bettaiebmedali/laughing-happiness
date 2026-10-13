from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="Python DevOps Demo", version="1.0.0")


class SumRequest(BaseModel):
    a: float = Field(..., description="First operand")
    b: float = Field(..., description="Second operand")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {"service": "python-devops-demo", "version": "1.0.0"}


@app.post("/sum")
def sum_values(payload: SumRequest):
    return {"result": payload.a + payload.b}

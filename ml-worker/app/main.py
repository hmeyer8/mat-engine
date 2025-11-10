from fastapi import FastAPI, Request
from pydantic import BaseModel
import numpy as np
import uvicorn

app = FastAPI()

class NDVIRequest(BaseModel):
    red: float
    nir: float

@app.get("/ping")
def ping():
    return {"status": "ok", "message": "ML worker online"}

@app.post("/predict")
async def predict(data: NDVIRequest):
    ndvi = (data.nir - data.red) / (data.nir + data.red + 1e-5)
    result = {"ndvi": round(ndvi, 3)}
    return {"status": "ok", "result": result}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)

import dill
import pandas as pd
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator
from typing import Literal
import uvicorn

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Modelni yuklash
with open("best_model_pipeline.dill", "rb") as f:
    model = dill.load(f)

# Har bir kategoriya maydoni uchun ruxsat berilgan qiymatlar
VALID_VALUES = {
    "SeniorCitizen": {0, 1},
    "Partner": {"Yes", "No"},
    "Dependents": {"Yes", "No"},
    "PhoneService": {"Yes", "No"},
    "MultipleLines": {"Yes", "No", "No phone service"},
    "InternetService": {"Fiber optic", "DSL", "No"},
    "OnlineSecurity": {"Yes", "No", "No internet service"},
    "OnlineBackup": {"Yes", "No", "No internet service"},
    "DeviceProtection": {"Yes", "No", "No internet service"},
    "TechSupport": {"Yes", "No", "No internet service"},
    "StreamingTV": {"Yes", "No", "No internet service"},
    "StreamingMovies": {"Yes", "No", "No internet service"},
    "Contract": {"Month-to-month", "One year", "Two year"},
    "PaperlessBilling": {"Yes", "No"},
    "PaymentMethod": {
        "Electronic check", "Mailed check", "Bank transfer (automatic)", "Credit card (automatic)"
    }
}


# Pydantic model
class ChurnInput(BaseModel):
    SeniorCitizen: int = Field(..., ge=0, le=1)
    Partner: str
    Dependents: str
    tenure: int = Field(..., ge=0)
    PhoneService: str
    MultipleLines: str
    InternetService: str
    OnlineSecurity: str
    OnlineBackup: str
    DeviceProtection: str
    TechSupport: str
    StreamingTV: str
    StreamingMovies: str
    Contract: str
    PaperlessBilling: str
    PaymentMethod: str
    MonthlyCharges: float = Field(..., ge=0)
    TotalCharges: float = Field(..., ge=0)

    # Validatorlar
    @field_validator("*", mode="before")
    @classmethod
    def check_valid_values(cls, v, info):
        field_name = info.field_name
        if field_name in VALID_VALUES:
            if v not in VALID_VALUES[field_name]:
                raise ValueError(f"{field_name} qiymati noto‘g‘ri: {v}")
        return v


@app.get("/", response_class=HTMLResponse)
async def get_form(request: Request):
    return templates.TemplateResponse("front.html", {"request": request})


@app.post("/predict", response_class=HTMLResponse)
async def predict(
    request: Request,
    SeniorCitizen: int = Form(...),
    Partner: str = Form(...),
    Dependents: str = Form(...),
    tenure: int = Form(...),
    PhoneService: str = Form(...),
    MultipleLines: str = Form(...),
    InternetService: str = Form(...),
    OnlineSecurity: str = Form(...),
    OnlineBackup: str = Form(...),
    DeviceProtection: str = Form(...),
    TechSupport: str = Form(...),
    StreamingTV: str = Form(...),
    StreamingMovies: str = Form(...),
    Contract: str = Form(...),
    PaperlessBilling: str = Form(...),
    PaymentMethod: str = Form(...),
    MonthlyCharges: float = Form(...),
    TotalCharges: float = Form(...)
):
    try:
        # Inputni validatsiyadan o‘tkazish
        input_data = ChurnInput(
            SeniorCitizen=SeniorCitizen,
            Partner=Partner,
            Dependents=Dependents,
            tenure=tenure,
            PhoneService=PhoneService,
            MultipleLines=MultipleLines,
            InternetService=InternetService,
            OnlineSecurity=OnlineSecurity,
            OnlineBackup=OnlineBackup,
            DeviceProtection=DeviceProtection,
            TechSupport=TechSupport,
            StreamingTV=StreamingTV,
            StreamingMovies=StreamingMovies,
            Contract=Contract,
            PaperlessBilling=PaperlessBilling,
            PaymentMethod=PaymentMethod,
            MonthlyCharges=MonthlyCharges,
            TotalCharges=TotalCharges
        )

        # DataFrame ga aylantirish
        df = pd.DataFrame([input_data.dict()])

        # Model orqali bashorat
        probability = model.predict_proba(df)[0][1] * 100
        prediction = "Qolmaydi" if probability >= 50 else "Qoladi"
        confidence = probability if prediction == "Qolmaydi" else 100 - probability

        return templates.TemplateResponse(
            "front.html",
            {
                "request": request,
                "result": f"Natija: {prediction} ({confidence:.2f}% ishonchlilikda)"
            }
        )

    except Exception as e:
        return templates.TemplateResponse(
            "front.html",
            {
                "request": request,
                "error": f"Xato: {str(e)}"
            }
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

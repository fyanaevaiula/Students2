from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field

from repository import StudentRepository, load_students_from_csv, StudentGrade

# ---------- Схемы Pydantic ----------

class StudentCreate(BaseModel):
    last_name: str = Field(..., max_length=100)
    first_name: str = Field(..., max_length=100)
    faculty: str = Field(..., max_length=100)
    course: str = Field(..., max_length=200)
    grade: int = Field(..., ge=0, le=100)

class StudentUpdate(BaseModel):
    """Обновлять можно любые поля — те, что не переданы, останутся как были."""
    last_name: str | None = Field(None, max_length=100)
    first_name: str | None = Field(None, max_length=100)
    faculty: str | None = Field(None, max_length=100)
    course: str | None = Field(None, max_length=200)
    grade: int | None = Field(None, ge=0, le=100)

class StudentOut(StudentCreate):
    id: int


# ---------- Подключение репозитория к FastAPI ----------

repo = StudentRepository()

def get_repo() -> StudentRepository:
    return repo

@asynccontextmanager
async def lifespan(app: FastAPI):
    # при старте загружаем данные из CSV, если файл лежит рядом
    if Path("students.csv").exists():
        load_students_from_csv(repo, "students.csv")
    yield
    # здесь можно закрыть соединения, если понадобится

app = FastAPI(title="Students API", lifespan=lifespan)


def to_out(obj: StudentGrade) -> StudentOut:
    return StudentOut(
        id=obj.id,
        last_name=obj.last_name,
        first_name=obj.first_name,
        faculty=obj.faculty,
        course=obj.course,
        grade=obj.grade,
    )


# ---------- CRUD-эндпоинты ----------

@app.post("/students", response_model=StudentOut, status_code=201)
def create_student(data: StudentCreate, repository: StudentRepository = Depends(get_repo)):
    """Create — добавление новой записи."""
    obj = repository.insert(data.model_dump())
    return to_out(obj)

@app.get("/students", response_model=list[StudentOut])
def read_students(repository: StudentRepository = Depends(get_repo)):
    """Read — список всех записей."""
    return [to_out(o) for o in repository.select_all()]

@app.get("/students/{record_id}", response_model=StudentOut)
def read_student(record_id: int, repository: StudentRepository = Depends(get_repo)):
    """Read — одна запись по id."""
    obj = repository.select_by_id(record_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    return to_out(obj)

@app.put("/students/{record_id}", response_model=StudentOut)
def update_student(
    record_id: int,
    data: StudentUpdate,
    repository: StudentRepository = Depends(get_repo),
):
    """Update — частичное обновление записи по id."""
    updates = data.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="Пустое тело запроса")
    obj = repository.update(record_id, updates)
    if obj is None:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    return to_out(obj)

@app.delete("/students/{record_id}")
def delete_student(record_id: int, repository: StudentRepository = Depends(get_repo)):
    """Delete — удаление записи по id."""
    if not repository.delete(record_id):
        raise HTTPException(status_code=404, detail="Запись не найдена")
    return {"detail": "Запись удалена"}

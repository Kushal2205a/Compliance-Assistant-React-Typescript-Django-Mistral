import os
import re
import uuid
from typing import BinaryIO

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.review import Checklist


class ParsedControl:
    def __init__(self, control_id: str, name: str, description: str):
        self.control_id = control_id
        self.name = name
        self.description = description


class ChecklistService:
    def __init__(self, db: Session):
        self.db = db

    def _get_storage_path(self, review_id: uuid.UUID, filename: str) -> str:
        review_dir = os.path.join(settings.abs_storage_dir, str(review_id), "checklist")
        os.makedirs(review_dir, exist_ok=True)
        return os.path.join(review_dir, filename)

    def upload(
        self,
        review_id: uuid.UUID,
        filename: str,
        file: BinaryIO,
    ) -> Checklist:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "pdf"
        file_path = self._get_storage_path(review_id, filename)

        existing = (
            self.db.query(Checklist)
            .filter(Checklist.review_id == review_id)
            .first()
        )
        if existing:
            if os.path.exists(existing.file_path) and existing.file_path != file_path:
                os.remove(existing.file_path)
            self.db.delete(existing)
            self.db.commit()

        with open(file_path, "wb") as f:
            f.write(file.read())

        checklist = Checklist(
            id=uuid.uuid4(),
            review_id=review_id,
            filename=filename,
            file_path=file_path,
            format=ext,
            status="uploaded",
        )
        self.db.add(checklist)
        self.db.commit()
        self.db.refresh(checklist)
        return checklist

    def parse_checklist(self, file_path: str) -> list[ParsedControl]:
        ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else "pdf"
        if ext == "pdf":
            return self._parse_pdf(file_path)
        else:
            raise ValueError(f"Unsupported checklist format: {ext}")

    def _parse_pdf(self, file_path: str) -> list[ParsedControl]:
        import pdfplumber

        controls: list[ParsedControl] = []
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() or ""
                text += "\n"

        lines = [l.strip() for l in text.split("\n") if l.strip()]
        buffer = ""
        control_id = 0
        description_lines: list[str] = []

        def _flush_control():
            nonlocal control_id, buffer, description_lines
            if not buffer.strip():
                return
            name = buffer.strip().split("\n")[0][:80]
            desc = "\n".join(description_lines) if description_lines else buffer.strip()
            controls.append(
                ParsedControl(
                    control_id=f"C{control_id:03d}",
                    name=name,
                    description=desc,
                )
            )
            control_id += 1
            description_lines = []

        for line in lines:
            is_new_control = bool(re.match(r"^(?:\d+\.\d+|CC\d+\.\d+|[•●▶→*\-])\s+", line))

            if is_new_control:
                _flush_control()
                buffer = re.sub(r"^[•●▶→*\-]\s*", "", line)
            elif buffer:
                description_lines.append(line)

        _flush_control()

        if not controls and text.strip():
            controls.append(
                ParsedControl(
                    control_id="C001",
                    name=text.strip().split("\n")[0][:80],
                    description=text.strip()[:500],
                )
            )

        return controls

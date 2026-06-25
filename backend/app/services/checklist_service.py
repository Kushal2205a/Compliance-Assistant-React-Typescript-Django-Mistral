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
        review_dir = os.path.join(settings.storage_dir, str(review_id), "checklist")
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

        with open(file_path, "wb") as f:
            f.write(file.read())

        existing = (
            self.db.query(Checklist)
            .filter(Checklist.review_id == review_id)
            .first()
        )
        if existing:
            if os.path.exists(existing.file_path):
                os.remove(existing.file_path)
            self.db.delete(existing)
            self.db.commit()

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

        for line in lines:
            if re.match(r"^\d+\.\d+\s+", line) or re.match(r"^CC\d+\.\d+", line):
                if buffer.strip():
                    controls.append(
                        ParsedControl(
                            control_id=f"C{control_id:03d}",
                            name=buffer.strip().split("\n")[0][:80],
                            description=buffer.strip(),
                        )
                    )
                    control_id += 1
                buffer = line
            else:
                buffer += " " + line if buffer else line

        if buffer.strip():
            controls.append(
                ParsedControl(
                    control_id=f"C{control_id:03d}",
                    name=buffer.strip().split("\n")[0][:80],
                    description=buffer.strip(),
                )
            )

        if not controls and text.strip():
            controls.append(
                ParsedControl(
                    control_id="C001",
                    name=text.strip().split("\n")[0][:80],
                    description=text.strip()[:500],
                )
            )

        return controls

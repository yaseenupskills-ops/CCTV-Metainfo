import uuid

from fastapi.testclient import TestClient

FAKE_MP4 = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + b"\x00" * 100


def upload(
    client: TestClient,
    case_id: uuid.UUID,
    content: bytes,
    filename: str = "clip.mp4",
    mime: str = "video/mp4",
):
    return client.post(
        "/api/v1/evidence/upload",
        data={"case_id": str(case_id)},
        files={"file": (filename, content, mime)},
    )

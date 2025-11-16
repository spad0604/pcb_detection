# PCB Missing-Component Detection – Solution Architecture

## Goals
- Provide a Flutter desktop UI (Windows/macOS/Linux) that allows operators to curate PCB datasets, trigger model training, and run inference to flag boards with missing components.
- Back the UI with a Python-based microservice responsible for dataset persistence, lightweight feature extraction, model training, and inference.
- Keep both halves decoupled via a simple REST contract so that the Python service can evolve independently (e.g., swap in YOLO later) while Flutter focuses on UX responsiveness.

## High-Level Flow
1. **Dataset curation** – Operators drag/drop or browse for PCB images. Flutter keeps a local list for UX and sends each image to the Python API (`POST /api/dataset`) with an operator-provided label (`ok` vs `missing`).
2. **Training** – UI exposes hyper-parameters (number of epochs, train/test split). Flutter calls `POST /api/train` and then polls `GET /api/train/{jobId}` for progress. Python service extracts simple statistical features today (avg RGB, Laplacian variance) and fits a Logistic Regression model saved to `artifacts/model.joblib`.
3. **Inference** – Operator uploads a fresh board photo. Flutter sends it to `POST /api/inference`, receives a classification plus missing-component heat-map metadata (placeholder), and visualizes the result.
4. **Live conveyor feed** – Python exposes the latest inspection-camera frame via `GET /api/stream/frame` (MJPEG/WebSocket-compatible). Flutter polls every ~0.8s, renders the bytes in a panel, and allows pausing/resuming without blocking other workloads.
5. **Feedback loop** – Failed detections can be re-labeled and re-added to the dataset to continuously improve the model.

## Flutter Desktop (GetX)
- **Packages**: `get` for routing/state, `file_picker` for file selection, `dio` for multipart uploads, `intl` for formatting, `collection` utilities.
- **Layers**:
  - `services/api_service.dart` centralizes HTTP, base URL, and DTO serialization.
  - `models/*` describe DTOs shared with the backend (training status, inference result).
  - `modules/dashboard/…` contains GetX bindings, controller, and view widgets. Controller orchestrates dataset uploads, training jobs, inference requests, a live video feed, and exposes observable state to panels (Dataset, Training, Live Stream, Inference, Activity Log).
  - Responsive desktop-friendly layout built with `LayoutBuilder`, `Flex`, and `DataTable` for dataset previews. Drag-and-drop hooks can be added later.
- **Offline resilience**: controller caches pending uploads; UI surfaces backend connectivity errors via GetX snackbars.

## Python Backend
- FastAPI app served by Uvicorn (`Embedded/backend/main.py`).
- **Modules**:
  - `core/config.py` – settings (data dir, allowed image extensions, default hyper-params).
  - `models/dto.py` – Pydantic request/response schemas shared with Flutter.
  - `services/dataset_service.py` – persists metadata (JSON) + raw files inside `data/dataset/<label>/…`.
  - `services/training_service.py` – handles feature extraction (Pillow + NumPy), scikit-learn logistic regression, job tracking, and artifact persistence.
  - `services/inference_service.py` – loads trained model, runs predictions, computes confidence + placeholder missing-component map (list of coordinates to be replaced later by CV model output).
- Includes a `tests/test_feature_extractor.py` sanity check to keep feature pipeline verifiable without GPUs.

## Data Contract (initial draft)
| Endpoint | Payload | Response |
| --- | --- | --- |
| `POST /api/dataset` | multipart: `file`, `label` (`ok`\|`missing`) | `{id, label, createdAt}` |
| `GET /api/dataset` | – | `[{id, label, path, createdAt}]` |
| `POST /api/train` | `{epochs, testSplit}` | `{jobId}` |
| `GET /api/train/{jobId}` | – | `{status, progress, metrics}` |
| `POST /api/inference` | multipart `file` | `{isDefective, confidence, missingAreas}` |
| `GET /api/stream/frame` | – | raw bytes (JPEG) |

This contract is intentionally simple so both sides can iterate quickly. Once the Python service exposes a richer defect map (e.g., bounding boxes from a CNN), the Flutter view can extend the inference panel without reworking the upstream controllers.

"""
Face recognition utilities — ArcFace + RetinaFace via DeepFace.

Key design decisions
--------------------
* ALL faces in every gallery image are embedded (not just the first/largest).
  This is critical for group event photos where the target person may not be
  the dominant face.  face_embedding is stored as a JSON list-of-lists:
      [[emb_face0], [emb_face1], ...]   (each inner list is 512 floats)

* Cosine distance is used (range 0–2; 0 = identical).
  Threshold 0.60 works well for real-world event photos where the selfie
  is taken under different lighting/angle than the event shot.

* numpy arrays are always converted with .tolist() before saving to JSONField
  so they round-trip through JSON without type errors.

* If retinaface fails to detect any face, we automatically retry with the
  faster 'opencv' backend as a fallback so we don't silently miss faces.
"""

import logging
import numpy as np

logger = logging.getLogger(__name__)

MODEL_NAME        = "ArcFace"
DETECTOR_BACKEND  = "retinaface"
FALLBACK_DETECTOR = "opencv"
MATCH_THRESHOLD   = 0.60   # raised from 0.45 — handles lighting/angle variance


# ---------------------------------------------------------------------------
# Lazy import
# ---------------------------------------------------------------------------

def _get_deepface():
    try:
        from deepface import DeepFace  # noqa: PLC0415
        return DeepFace
    except (ImportError, AttributeError) as exc:
        raise ImportError(
            "DeepFace could not be loaded. Install with: pip install deepface tf-keras"
        ) from exc


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _represent(image_path: str, detector: str) -> list:
    """
    Run DeepFace.represent and return a list of raw result dicts.
    Returns [] if no face is detected (never raises on missing face).
    """
    DeepFace = _get_deepface()
    try:
        results = DeepFace.represent(
            img_path=image_path,
            model_name=MODEL_NAME,
            detector_backend=detector,
            enforce_detection=True,
            align=True,
        )
        return results if results else []
    except ValueError:
        # enforce_detection=True raises ValueError when no face found
        return []
    except Exception as exc:
        logger.warning("DeepFace.represent failed [%s] for %s: %s", detector, image_path, exc)
        return []


def _safe_tolist(embedding) -> list:
    """Convert numpy array or plain list to a plain Python list of floats."""
    if isinstance(embedding, np.ndarray):
        return embedding.tolist()
    if isinstance(embedding, list):
        # Ensure every element is a plain float (not np.float32)
        return [float(x) for x in embedding]
    return list(embedding)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_all_embeddings(image_path: str) -> list[list]:
    """
    Extract ArcFace embeddings for EVERY face detected in *image_path*.

    Returns:
        list[list[float]] — one 512-dim vector per detected face.
                            Empty list if no faces found.
    """
    results = _represent(image_path, DETECTOR_BACKEND)

    # Fallback: retry with opencv if retinaface found nothing
    if not results:
        logger.debug("retinaface found no faces in %s, retrying with opencv", image_path)
        results = _represent(image_path, FALLBACK_DETECTOR)

    embeddings = []
    for r in results:
        emb = r.get("embedding")
        if emb is not None:
            embeddings.append(_safe_tolist(emb))

    logger.debug("extract_all_embeddings: %d face(s) in %s", len(embeddings), image_path)
    return embeddings


def extract_single_embedding(image_path: str) -> list | None:
    """
    Extract a single ArcFace embedding (for a selfie that should contain
    exactly one face).

    Returns the embedding of the largest/first detected face, or None.
    """
    all_embs = extract_all_embeddings(image_path)
    return all_embs[0] if all_embs else None


def cosine_distance(vec_a: list, vec_b: list) -> float:
    """Cosine distance between two vectors (0 = identical, 2 = opposite)."""
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 1.0
    return float(1.0 - np.dot(a, b) / (norm_a * norm_b))


def best_distance_against_faces(selfie_emb: list, face_embeddings: list) -> float:
    """
    Return the minimum cosine distance between *selfie_emb* and any of the
    face embeddings stored for a gallery image.

    face_embeddings is a list-of-lists (one per detected face in the photo).
    """
    if not face_embeddings:
        return 1.0
    # Handle legacy format: a single flat list (old single-face storage)
    if face_embeddings and isinstance(face_embeddings[0], (int, float)):
        face_embeddings = [face_embeddings]
    return min(cosine_distance(selfie_emb, fe) for fe in face_embeddings)


# ---------------------------------------------------------------------------
# Batch search
# ---------------------------------------------------------------------------

def find_matching_gallery_images(
    selfie_embedding: list,
    gallery_qs,
    threshold: float = MATCH_THRESHOLD,
):
    """
    Compare *selfie_embedding* against every face stored in every GalleryImage
    in *gallery_qs* (embedding_status='done').

    Returns:
        list of (distance, GalleryImage) tuples sorted ascending by distance,
        filtered to those where best_distance <= threshold.
    """
    candidates = (
        gallery_qs
        .filter(embedding_status="done")
        .exclude(face_embedding__isnull=True)
    )

    matches = []
    all_scores = []  # for debug logging

    for img in candidates:
        try:
            dist = best_distance_against_faces(selfie_embedding, img.face_embedding)
            all_scores.append((img.id, dist))
            if dist <= threshold:
                matches.append((dist, img))
        except Exception as exc:
            logger.warning("Comparison failed for GalleryImage %s: %s", img.id, exc)

    # Always log scores so you can see them in Django logs
    logger.info(
        "Face search scores (threshold=%.2f): %s",
        threshold,
        ", ".join(f"img#{i}={d:.4f}" for i, d in sorted(all_scores, key=lambda x: x[1])),
    )

    matches.sort(key=lambda x: x[0])
    return matches   # list of (distance, GalleryImage)


# ---------------------------------------------------------------------------
# Embedding generation / re-indexing
# ---------------------------------------------------------------------------

def generate_embedding_for_gallery_image(gallery_image) -> str:
    """
    Extract and persist ArcFace embeddings for ALL faces in a GalleryImage.

    face_embedding is stored as list-of-lists:
        [[emb_face0_float, ...], [emb_face1_float, ...], ...]

    Returns one of: 'done', 'no_face', 'error'.
    """
    try:
        all_embeddings = extract_all_embeddings(gallery_image.image.path)

        if not all_embeddings:
            gallery_image.face_embedding    = None
            gallery_image.embedding_status  = "no_face"
        else:
            gallery_image.face_embedding    = all_embeddings   # list of lists
            gallery_image.embedding_status  = "done"

        gallery_image.save(update_fields=["face_embedding", "embedding_status"])
        logger.info(
            "GalleryImage %s: %d face(s) indexed",
            gallery_image.id,
            len(all_embeddings),
        )
        return gallery_image.embedding_status

    except Exception as exc:
        logger.error(
            "Error generating embedding for GalleryImage %s: %s",
            gallery_image.id, exc,
        )
        gallery_image.embedding_status = "error"
        gallery_image.save(update_fields=["embedding_status"])
        return "error"

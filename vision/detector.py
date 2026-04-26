import cv2
import numpy as np
import config
from utils.logger import log

_POSITION_COLOURS = {
    "left":   (255, 140, 0),
    "center": (0, 220, 0),
    "right":  (0, 100, 255),
}


class VisionDetector:
    def __init__(self):
        from ultralytics import YOLO
        self.model = YOLO("yolov8n.pt")  # auto-downloaded on first run
        self.cam = cv2.VideoCapture(0)
        self.cam.set(cv2.CAP_PROP_FRAME_WIDTH,  config.CAMERA_RESOLUTION[0])
        self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_RESOLUTION[1])
        log("YOLOv8n detector ready.", level="info")

    def _run_detection(self, frame: np.ndarray) -> list:
        h, w = frame.shape[:2]
        results = self.model(frame, verbose=False)[0]
        detections = []
        for box in results.boxes:
            conf = float(box.conf[0])
            if conf < config.DETECTION_CONFIDENCE_THRESHOLD:
                continue
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cx = (x1 + x2) // 2
            if cx < w // 3:
                position = "left"
            elif cx > 2 * w // 3:
                position = "right"
            else:
                position = "center"
            label = results.names[int(box.cls[0])]
            detections.append({
                "label":      label,
                "confidence": conf,
                "position":   position,
                "bbox":       (x1, y1, x2, y2),
            })
        return detections

    def detect(self) -> list:
        _, frame = self.cam.read()
        return self._run_detection(frame)

    def annotate(self, frame: np.ndarray, detections: list) -> np.ndarray:
        out = frame.copy()
        h, w = out.shape[:2]

        cv2.line(out, (w // 3, 0),     (w // 3, h),     (60, 60, 60), 1)
        cv2.line(out, (2 * w // 3, 0), (2 * w // 3, h), (60, 60, 60), 1)
        cv2.putText(out, "LEFT",   (8, 18),          cv2.FONT_HERSHEY_SIMPLEX, 0.45, (80, 80, 80), 1)
        cv2.putText(out, "CENTER", (w // 2 - 28, 18),cv2.FONT_HERSHEY_SIMPLEX, 0.45, (80, 80, 80), 1)
        cv2.putText(out, "RIGHT",  (2*w//3 + 8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (80, 80, 80), 1)

        for d in detections:
            x1, y1, x2, y2 = d["bbox"]
            colour = _POSITION_COLOURS.get(d["position"], (0, 255, 0))
            label  = f"{d['label']} {d['confidence']:.0%} [{d['position']}]"
            cv2.rectangle(out, (x1, y1), (x2, y2), colour, 2)
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(out, (x1, y1 - th - 6), (x1 + tw + 4, y1), colour, -1)
            cv2.putText(out, label, (x1 + 2, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        return out

    def stop(self):
        self.cam.release()

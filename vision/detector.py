import cv2
import numpy as np
import config

CLASSES = [
    "background", "aeroplane", "bicycle", "bird", "boat",
    "bottle", "bus", "car", "cat", "chair", "cow",
    "diningtable", "dog", "horse", "motorbike", "person",
    "pottedplant", "sheep", "sofa", "train", "tvmonitor"
]

# Colours per class for bounding box display (BGR)
_BOX_COLOUR  = (0, 255, 0)    # green boxes
_TEXT_COLOUR = (0, 255, 0)
_LEFT_COLOUR  = (255, 100, 0) # blue tint for left
_RIGHT_COLOUR = (0, 100, 255) # red tint for right
_CENTER_COLOUR = (0, 255, 0)  # green for center

_POSITION_COLOURS = {
    "left":   (255, 140, 0),
    "center": (0, 220, 0),
    "right":  (0, 100, 255),
}


class VisionDetector:
    def __init__(self):
        self.net = cv2.dnn.readNetFromCaffe(
            config.DETECTION_PROTOTXT,
            config.DETECTION_MODEL
        )
        self.cam = cv2.VideoCapture(0)
        self.cam.set(cv2.CAP_PROP_FRAME_WIDTH,  config.CAMERA_RESOLUTION[0])
        self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_RESOLUTION[1])

    def _run_detection(self, frame: np.ndarray) -> list:
        """Run MobileNet SSD on a frame and return detection results."""
        h, w = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(
            cv2.resize(frame, (300, 300)),
            0.007843, (300, 300), 127.5
        )
        self.net.setInput(blob)
        raw = self.net.forward()
        results = []

        for i in range(raw.shape[2]):
            confidence = raw[0, 0, i, 2]
            if confidence < config.DETECTION_CONFIDENCE_THRESHOLD:
                continue
            idx = int(raw[0, 0, i, 1])
            box = raw[0, 0, i, 3:7] * np.array([w, h, w, h])
            x1, y1, x2, y2 = box.astype("int")
            cx = (x1 + x2) // 2

            if cx < w // 3:
                position = "left"
            elif cx > 2 * w // 3:
                position = "right"
            else:
                position = "center"

            results.append({
                "label":      CLASSES[idx],
                "confidence": float(confidence),
                "position":   position,
                "bbox":       (x1, y1, x2, y2)
            })

        return results

    def detect(self) -> list:
        """Capture a frame and return detections. Standard usage for agent loop."""
        _, frame = self.cam.read()
        return self._run_detection(frame)

    def detect_with_frame(self) -> tuple:
        """
        Capture a frame, run detection, and return (detections, annotated_frame).
        The annotated frame has bounding boxes and labels drawn on it.
        Use this when you want to display the camera feed on a monitor.
        """
        _, frame   = self.cam.read()
        detections = self._run_detection(frame)
        annotated  = self.annotate(frame, detections)
        return detections, annotated

    def annotate(self, frame: np.ndarray, detections: list) -> np.ndarray:
        """
        Draw bounding boxes, labels, confidence scores, and position zones
        onto a copy of the frame. Returns the annotated copy.
        """
        out = frame.copy()
        h, w = out.shape[:2]

        # Draw the three position zone dividers (subtle vertical lines)
        cv2.line(out, (w // 3, 0),     (w // 3, h),     (60, 60, 60), 1)
        cv2.line(out, (2 * w // 3, 0), (2 * w // 3, h), (60, 60, 60), 1)

        # Zone labels at top
        cv2.putText(out, "LEFT",   (8, 18),         cv2.FONT_HERSHEY_SIMPLEX, 0.45, (80, 80, 80), 1)
        cv2.putText(out, "CENTER", (w//2 - 28, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (80, 80, 80), 1)
        cv2.putText(out, "RIGHT",  (2*w//3 + 8, 18),cv2.FONT_HERSHEY_SIMPLEX, 0.45, (80, 80, 80), 1)

        for d in detections:
            x1, y1, x2, y2 = d["bbox"]
            colour = _POSITION_COLOURS.get(d["position"], _BOX_COLOUR)
            label  = f"{d['label']} {d['confidence']:.0%} [{d['position']}]"

            cv2.rectangle(out, (x1, y1), (x2, y2), colour, 2)

            # Label background
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(out, (x1, y1 - th - 6), (x1 + tw + 4, y1), colour, -1)
            cv2.putText(out, label, (x1 + 2, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

        return out

    def stop(self):
        self.cam.release()

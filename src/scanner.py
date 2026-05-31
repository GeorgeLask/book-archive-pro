import time

import cv2
from pyzbar.pyzbar import decode


class BarcodeScanner:
    def __init__(self, camera_id=0, cooldown=3.0):
        self.camera_id = camera_id
        # Seconds to suppress re-emitting the same ISBN. While a book is held
        # to the camera the same barcode decodes ~30x/sec; the cooldown means
        # one held book yields one event.
        self.cooldown = cooldown

    def scan(self):
        """
        Opens the camera and yields detected ISBNs.
        Press 'q' to stop scanning.
        """
        cap = cv2.VideoCapture(self.camera_id)

        print("Scanner active. Hold the barcode up to the camera. Press 'q' to quit.")

        # Maps a recently seen ISBN -> the time it was last yielded.
        last_seen = {}

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Decode barcodes in the frame
            barcodes = decode(frame)
            for barcode in barcodes:
                isbn = barcode.data.decode("utf-8")
                # Draw a rectangle around the barcode for visual feedback
                (x, y, w, h) = barcode.rect
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

                now = time.monotonic()
                if now - last_seen.get(isbn, 0.0) < self.cooldown:
                    continue
                last_seen[isbn] = now

                # Yield the ISBN so the main loop can process it
                yield isbn

            # Display the camera feed
            cv2.imshow("Book Archive Scanner", frame)

            # Break on 'q' key
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        cap.release()
        cv2.destroyAllWindows()

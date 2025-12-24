import cv2
from pyzbar.pyzbar import decode


class BarcodeScanner:
    def __init__(self, camera_id=0):
        self.camera_id = camera_id

    def scan(self):
        """
        Opens the camera and yields detected ISBNs.
        Press 'q' to stop scanning.
        """
        cap = cv2.VideoCapture(self.camera_id)

        print("Scanner active. Hold the barcode up to the camera. Press 'q' to quit.")

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

                # Yield the ISBN so the main loop can process it
                yield isbn

            # Display the camera feed
            cv2.imshow("Book Archive Scanner", frame)

            # Break on 'q' key
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        cap.release()
        cv2.destroyAllWindows()

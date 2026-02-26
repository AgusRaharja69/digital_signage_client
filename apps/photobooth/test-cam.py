import cv2

cap = cv2.VideoCapture(0, cv2.CAP_V4L2)

if not cap.isOpened():
    print("Kamera tidak bisa dibuka")
    exit()

print("Kamera berhasil dibuka")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Gagal ambil frame")
        break

    cv2.imshow("Webcam Test", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
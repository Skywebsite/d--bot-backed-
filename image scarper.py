from paddleocr import PaddleOCR

ocr = PaddleOCR(
    lang="en",
    use_textline_orientation=True
)

result = ocr.predict(r"C:\Users\lenovo\Desktop\modern-glossy-music-event-poster-design-template-84d38a706368baec17981e71a5e5810d_screen.jpg")

texts = result[0]["rec_texts"]
scores = result[0]["rec_scores"]

for t, s in zip(texts, scores):
    print(t, s)
